import os
import json
import time
import base64
from io import BytesIO
import subprocess

import pyautogui
from PIL import Image, ImageGrab, ImageDraw, ImageFont
from openai import OpenAI
from dotenv import load_dotenv
from prompts import SYSTEM_PROMPT_TEXT, DEFAULT_PROMPT


# ---------------------------------------------------------------------------- #
#                                     TODO                                     #
# ---------------------------------------------------------------------------- #

#  TODO: Test to understant if this exception is for human mouse movement, automated movement, or both.
    # raise FailSafeException(
    #         "PyAutoGUI fail-safe triggered from mouse moving to a corner of the screen. To disable this fail-safe, set pyautogui.FAILSAFE to False. DISABLING FAIL-SAFE IS NOT RECOMMENDED."
    #     )

# TODO: iterate on algorithm to improve its ability to conduct tasks

# TODO: Create bite maker for complex tasks.

# TODO: Create router to decide if task is complex or direct.
 
# =============================================================================
# Constants
# =============================================================================


load_dotenv()

# Environment variable keys
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
client = OpenAI(base_url = 'http://127.0.0.1:1234/v1')

# Grid and drawing settings
GRID_SIZE = 2
GRID_COLOR = "red"
GRID_LINE_WIDTH = 2

FONT_SIZE_FACTOR = 0.5      # Used when the truetype font is available
FONT_FALLBACK_FACTOR = 0.25   # Used if truetype font fails

# Mouse movement settings
MOUSE_MOVE_DURATION = 0.5

MODEL_NAME = "qwen2-vl-7b-instruct"

# -------------------------------- Create Grid ------------------------------- #

def add_grid_and_numbers(image, grid_size=GRID_SIZE):
    """Add grid lines and numbers to the image."""
    img_copy = image.copy()
    draw = ImageDraw.Draw(img_copy)
    width, height = image.size
    cell_width = width // grid_size
    cell_height = height // grid_size

    font = ImageFont.load_default(size=int(cell_height * FONT_SIZE_FACTOR))

    # Draw vertical grid lines
    for i in range(1, grid_size):
        x = i * cell_width
        draw.line([(x, 0), (x, height)], fill=GRID_COLOR, width=GRID_LINE_WIDTH)

    # Draw horizontal grid lines
    for i in range(1, grid_size):
        y = i * cell_height
        draw.line([(0, y), (width, y)], fill=GRID_COLOR, width=GRID_LINE_WIDTH)

    # Draw numbers in the center of each cell
    for i in range(grid_size):
        for j in range(grid_size):
            number = i * grid_size + j + 1
            text = str(number)
            # Get text size for centering
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = j * cell_width + cell_width // 2 - text_width // 2
            y = i * cell_height + cell_height // 2 - text_height // 2
            draw.text((x, y), text, fill=GRID_COLOR, font=font)

    return img_copy

# ----------------------------- Image Processing ----------------------------- #

def encode_image_to_base64(image):
    """Convert a PIL Image to a base64 string."""
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def crop_to_cell(image, cell_number, grid_size=GRID_SIZE, output_size=None):
    """
    Crop the image to the specified grid cell.
    If output_size is provided, resize the cropped cell to that size.
    """
    width, height = image.size
    cell_width = width // grid_size
    cell_height = height // grid_size

    # Convert cell_number (1-indexed) to row and column (0-indexed)
    index = cell_number - 1
    row = index // grid_size
    col = index % grid_size

    left = col * cell_width
    upper = row * cell_height
    right = left + cell_width
    lower = upper + cell_height

    cropped = image.crop((left, upper, right, lower))
    if output_size is not None:
        cropped = cropped.resize(output_size, Image.LANCZOS)
    return cropped

def move_mouse_to_cell(cell_number, region_offset, region_size, grid_size=GRID_SIZE, duration=MOUSE_MOVE_DURATION, scale=(1.0, 1.0)):
    """
    Compute the center of the specified cell (within the region defined by region_offset and region_size)
    and move the mouse pointer there.
    The `scale` tuple adjusts for differences between screenshot and display coordinate spaces.
    """
    region_width, region_height = region_size
    # Determine the row and column (0-indexed)
    index = cell_number - 1
    row = index // grid_size
    col = index % grid_size

    # Compute the center within the region:
    cell_width = region_width // grid_size
    cell_height = region_height // grid_size

    center_x = region_offset[0] + col * cell_width + cell_width // 2
    center_y = region_offset[1] + row * cell_height + cell_height // 2

    # Adjust for the scaling between the screenshot and actual screen coordinates:
    center_x = int(center_x * scale[0])
    center_y = int(center_y * scale[1])

    print(f"Moving mouse to cell {cell_number} at ({center_x}, {center_y})")
    pyautogui.moveTo(center_x, center_y, duration=duration)


# ------------------------------ Vision API call ----------------------------- #

def GPT_Vision_Call(prompt=DEFAULT_PROMPT, image=None, message_history=None):
    """
    Sends the conversation (including full history) along with the current prompt and image to GPT-4 Vision.
    """

    base64_image = encode_image_to_base64(image)

    message_history.append({
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
        ]
    })

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            # response_format={"type": "json_object"},
            messages=message_history,
            max_tokens=500
        )
        # Get assistant's message and add it to the conversation history.
        assistant_message = response.choices[0].message.content
        message_history.append({
            "role": "assistant",
            "content": assistant_message
        })

        return assistant_message, message_history

    except Exception as e:
        error_msg = json.dumps({"error": str(e)})
        message_history.append({
            "role": "assistant",
            "content": error_msg
        })
        return error_msg, message_history

def capture_screenshot_with_cursor(output_file="screenshot.png"):
    """Capture a screenshot including the mouse cursor using macOS's screencapture command."""
    subprocess.run(["screencapture", "-C", output_file], check=True)
    return Image.open(output_file)


# ----------------------------------- MAIN ----------------------------------- #

def main():
    prompt = DEFAULT_PROMPT  # This can be dynamic or come from another source

    # Capture the full screenshot.
    original_screenshot = capture_screenshot_with_cursor()
    screenshot_size = original_screenshot.size  # (width, height)

    # Get the actual screen size from PyAutoGUI.
    actual_screen_size = pyautogui.size()  # (width, height)
    
    # Compute scaling factors between screenshot and actual screen coordinates.
    scale = (actual_screen_size[0] / screenshot_size[0],
             actual_screen_size[1] / screenshot_size[1])

    # Define initial region as the full screenshot.
    current_offset = (0, 0)
    current_region_size = screenshot_size

    iteration = 1  # Image saving counter

    # Initialize the conversation history list with the system prompt.
    message_history = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT_TEXT
        }
    ]

    while True:
        # Crop the current region from the original screenshot.
        current_region = original_screenshot.crop((
            current_offset[0],
            current_offset[1],
            current_offset[0] + current_region_size[0],
            current_offset[1] + current_region_size[1]
        ))

        # Upscale the cropped region to the actual screen size for consistency.
        current_region_upscaled = current_region.resize(actual_screen_size, Image.LANCZOS)

        current_region_with_grid = add_grid_and_numbers(current_region_upscaled)
        
        # Save the grid image with a sequential filename.
        image_filename = f"grid-image-{iteration}.png"
        current_region_with_grid.save(image_filename)
        print(f"Saved grid image: {image_filename}")
        iteration += 1

        # Call GPT-4 Vision with the current region and full conversation history.
        response, message_history = GPT_Vision_Call(prompt, image=current_region_with_grid, message_history=message_history)
        print("GPT-4 Vision Response:", response)

        try:
            parsed_response = json.loads(response)
        except Exception as e:
            print("Error parsing response:", e)
            break

        action = parsed_response.get("action")
        action_value = parsed_response.get("actionValue")
        cell_number = 1
        continue_zoom = True

        # Move the mouse to the center of the chosen cell.
        if action == "move_mouse":
            cell_number = int(action_value)
            move_mouse_to_cell(cell_number, current_offset, current_region_size, grid_size=GRID_SIZE, duration=MOUSE_MOVE_DURATION, scale=scale)
            print(f"Moved mouse to cell {cell_number}.")

        if action == "click":
            pyautogui.click()
            print("Mouse clicked on the cell.")
            continue_zoom = False
            
        if action == "type":
            pyautogui.typewrite(action_value)
            print(f"Typed '{action_value}'")
            continue_zoom = False

        # Wait for action to fully complete before capturing the next screenshot.
        time.sleep(1)

        # Capture a new screenshot after the action.
        original_screenshot = capture_screenshot_with_cursor()

        if continue_zoom:
            # Update the region to zoom in to the chosen cell.
            cell_width = current_region_size[0] // GRID_SIZE
            cell_height = current_region_size[1] // GRID_SIZE
            row = (cell_number - 1) // GRID_SIZE
            col = (cell_number - 1) % GRID_SIZE
            new_offset = (current_offset[0] + col * cell_width,
                          current_offset[1] + row * cell_height)
            new_region_size = (cell_width, cell_height)
            print(f"Zooming in to cell {cell_number}: New offset {new_offset}, New region size {new_region_size}")
            current_offset, current_region_size = new_offset, new_region_size
        else:
            # Reset the region to the full screenshot.
            current_offset = (0, 0)
            current_region_size = screenshot_size
            print("Resetting to full screenshot.")

if __name__ == "__main__":
    main()