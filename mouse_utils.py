import pyautogui
from constants import SCREENSHOT_GRID_DIVISION_NUM

def move_mouse_to_cell(cell_number: int, region_offset: tuple, region_size: tuple, duration: float = 0.5, scale: tuple = (1.0, 1.0)) -> None:
    """
    Calculates the center of the specified cell within a region and moves the mouse there.
    """
    region_width, region_height = region_size

    index = cell_number - 1
    row = index // SCREENSHOT_GRID_DIVISION_NUM
    col = index % SCREENSHOT_GRID_DIVISION_NUM

    cell_width = region_width // SCREENSHOT_GRID_DIVISION_NUM
    cell_height = region_height // SCREENSHOT_GRID_DIVISION_NUM
    center_x = region_offset[0] + col * cell_width + cell_width // 2
    center_y = region_offset[1] + row * cell_height + cell_height // 2

    # Adjust for scale differences
    center_x = int(center_x * scale[0])
    center_y = int(center_y * scale[1])

    print(f"Moving mouse to cell {cell_number} at ({center_x}, {center_y})")
    pyautogui.moveTo(center_x, center_y, duration=duration)
