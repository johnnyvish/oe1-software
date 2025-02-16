import re
import pyautogui
import time
import os
import json
import time
import base64
from io import BytesIO
import subprocess

import pyautogui
from PIL import Image, ImageGrab, ImageDraw, ImageFont
from prompts import SYSTEM_PROMPT_TEXT, DEFAULT_PROMPT, VALIDATION_PROMPT


# Example output from the vision model
vision_output = "<|box_start|>(108,765),(234,819)<|box_end|>"

MODEL_NAME = "os-atlas-base-7b"

# ---------------------------------------------------------------------------- #
#                                 OPENAI STUFF                                 #
# ---------------------------------------------------------------------------- #

from openai import OpenAI
from dotenv import load_dotenv
# from prompts import DEFAULT_PROMPT

load_dotenv()


DEFAULT_PROMPT = "Locate python debugger in this image"

# Environment variable keys
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
client = OpenAI(base_url = 'http://127.0.0.1:1234/v1')

# Add this to the Constants section
USE_MESSAGE_HISTORY = False  # New flag to control message history

def GPT_Vision_Call(prompt=DEFAULT_PROMPT, image=None, message_history=None):
    """
    Sends the conversation (including full history) along with the current prompt and image to GPT-4 Vision.
    """
    base64_image = encode_image_to_base64(image)
    
    # Create the message list based on USE_MESSAGE_HISTORY flag
    if USE_MESSAGE_HISTORY and message_history:
        messages = message_history
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
            ]
        })
    else:
        # Just use system prompt and current message
        messages = [
            {
                "role": "system",
                "content": ""
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                ]
            }
        ]

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            # max_tokens=500
            temperature=0.0
        )
        # Get assistant's message
        assistant_message = response.choices[0].message.content
        
        # Only update message history if we're using it
        if USE_MESSAGE_HISTORY and message_history is not None:
            message_history.append({
                "role": "assistant",
                "content": assistant_message
            })
            return assistant_message, message_history
        else:
            return assistant_message, None

    except Exception as e:
        error_msg = json.dumps({"error": str(e)})
        if USE_MESSAGE_HISTORY and message_history is not None:
            message_history.append({
                "role": "assistant",
                "content": error_msg
            })
            return error_msg, message_history
        else:
            return error_msg, None

# --------------------- Image capture and pre-processing --------------------- #

def capture_screenshot_with_cursor(output_file="screenshot.png"):
    """Capture a screenshot including the mouse cursor using macOS's screencapture command."""
    subprocess.run(["screencapture", "-C", output_file], check=True)
    img = Image.open(output_file)
    
    # Get original dimensions
    width, height = img.size
    
    # Calculate new dimensions (1/4 of original)
    new_width = width // 2
    new_height = height // 2
    
    # Crop the image to the top-left quarter
    cropped_img = img.crop((0, 0, new_width, new_height))
    
    # Save the cropped image
    cropped_img.save(output_file)
    return cropped_img


def encode_image_to_base64(image):
    """Convert a PIL Image to a base64 string."""
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

# ----------------------------- Translate Action ----------------------------- #

def parse_box(output):
    """
    Parses the vision model output to extract the box coordinates.
    Handles multiple formats:
    1. "<|box_start|>(x1,y1),(x2,y2)<|box_end|>"
    2. "<|box_start|>[[x1, y1], [x2, y2]]<|box_end|>"
    3. "<|box_start|>[[x1, y1, x2, y2]]<|box_end|>"
    Returns a tuple of integers: (x1, y1, x2, y2)
    """
    # Try the first format (x1,y1),(x2,y2)
    pattern1 = r"<\|box_start\|>\((\d+),\s*(\d+)\),\((\d+),\s*(\d+)\)<\|box_end\|>"
    match = re.search(pattern1, output)
    if match:
        return tuple(map(int, match.groups()))
    
    # Try the second format [[x1, y1], [x2, y2]]
    pattern2 = r"<\|box_start\|>\[\[(\d+),\s*(\d+)\],\s*\[(\d+),\s*(\d+)\]\]<\|box_end\|>"
    match = re.search(pattern2, output)
    if match:
        return tuple(map(int, match.groups()))
    
    # Try the third format [[x1, y1, x2, y2]]
    pattern3 = r"<\|box_start\|>\[\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]\]<\|box_end\|>"
    match = re.search(pattern3, output)
    if match:
        return tuple(map(int, match.groups()))
    
    raise ValueError(f"Box format not recognized in output: {output}")

# ------------------------------ EXECUTE ACTION ------------------------------ #

def move_to_box_center(box):
    """
    Calculates the center coordinate of the box and moves the mouse there.
    """
    x1, y1, x2, y2 = box
    center_x = (x1 + x2) // 2
    center_y = (y1 + y2) // 2

    print(f"Moving mouse to center: ({center_x}, {center_y})")
    # Adding a short delay so you can see the movement in action
    time.sleep(1)
    pyautogui.moveTo(center_x, center_y, duration=0.5)

def draw_box_on_image(image, box, output_path="/Users/ak./Documents/oe1-software/annotated_screenshot.png"):
    """
    Draws a red box on the image based on the coordinates and saves it.
    
    Args:
        image: PIL Image object
        box: Tuple of (x1, y1, x2, y2) coordinates
        output_path: Path where the annotated image should be saved
    """
    # Create a copy of the image to avoid modifying the original
    annotated_image = image.copy()
    draw = ImageDraw.Draw(annotated_image)
    
    # Draw red rectangle with line width of 2 pixels
    draw.rectangle(box, outline='red', width=2)
    
    # Save the annotated image
    annotated_image.save(output_path)
    print(f"Annotated image saved to: {output_path}")
    return annotated_image

if __name__ == '__main__':
    try:
        # Initialize message_history if we're using it
        message_history = [] if USE_MESSAGE_HISTORY else None
        
        original_screenshot = capture_screenshot_with_cursor()
        
        response, message_history = GPT_Vision_Call(DEFAULT_PROMPT, image=original_screenshot, message_history=message_history)
        print("GPT-4 Vision Response:", response)

        # Call GPT-4 Vision with the current region and full conversation history.
        box = parse_box(response)  # Changed from vision_output to response
        
        # Draw and save the annotated image
        draw_box_on_image(original_screenshot, box)
        
        move_to_box_center(box)

    except Exception as e:
        print(f"Error: {e}")