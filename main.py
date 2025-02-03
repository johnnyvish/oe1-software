import json
import time
import pyautogui
from PIL import ImageGrab
from PIL import Image
from mouse_utils import move_mouse_to_cell
from gpt_utils import call_gpt_vision
from constants import SCREENSHOT_GRID_DIVISION_NUM

def main() -> None:
    """
    Main execution function:
      - Starts the agentic process
    """
    prompt = "Play Pink Floyd"  # Adjust the prompt as needed.

    # Capture a full-screen screenshot.
    original_screenshot = ImageGrab.grab()
    screenshot_size = original_screenshot.size  # (width, height)

    # Get actual screen dimensions.
    actual_screen_size = pyautogui.size()  # (width, height)

    # Compute scaling factors.
    scale = (actual_screen_size[0] / screenshot_size[0],
             actual_screen_size[1] / screenshot_size[1])

    # Define the initial region as the full screenshot.
    current_offset = (0, 0)                # Top-left corner of the region
    current_region_size = screenshot_size  # Region size (width, height)

    while True:
        # Crop current region from the screenshot.
        current_region = ImageGrab.grab(bbox=(
            current_offset[0],
            current_offset[1],
            current_offset[0] + current_region_size[0],
            current_offset[1] + current_region_size[1]
        ))
        # Upscale the region to match the actual screen size.
        current_region_upscaled = current_region.resize(actual_screen_size, Image.LANCZOS)

        # Query GPT-4 Vision for instructions.
        response = call_gpt_vision(prompt, image=current_region_upscaled)
        print("GPT-4 Vision Response:", response)

        try:
            parsed_response = json.loads(response)
        except Exception as e:
            print("Error parsing response:", e)
            break

        # Extract instructions from the response.
        cell_number = parsed_response.get("cell_number")
        click_flag = parsed_response.get("click", False)
        continue_zoom = parsed_response.get("continue_zoom", False)

        if cell_number is None:
            print("No cell number returned from GPT-4 Vision. Ending operation.")
            break

        # Move the mouse to the center of the chosen cell.
        move_mouse_to_cell(cell_number, current_offset, current_region_size, scale=scale)
        time.sleep(2)  # Wait for the movement to complete.

        if click_flag:
            pyautogui.click()
            print("Mouse clicked on the cell.")
            break

        if continue_zoom:
            cell_width = current_region_size[0] // SCREENSHOT_GRID_DIVISION_NUM
            cell_height = current_region_size[1] // SCREENSHOT_GRID_DIVISION_NUM
            row = (cell_number - 1) // SCREENSHOT_GRID_DIVISION_NUM
            col = (cell_number - 1) % SCREENSHOT_GRID_DIVISION_NUM
            new_offset = (current_offset[0] + col * cell_width,
                          current_offset[1] + row * cell_height)
            new_region_size = (cell_width, cell_height)
            print(f"Zooming in to cell {cell_number}: New offset {new_offset}, New region size {new_region_size}")
            current_offset, current_region_size = new_offset, new_region_size
        else:
            print("No further zoom instructed. Ending loop.")
            break

if __name__ == "__main__":
    main()
