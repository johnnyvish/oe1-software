import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from constants import SCREENSHOT_GRID_DIVISION_NUM, SCREENSHOT_GRID_LINE_WIDTH

def read_prompt_from_file(file_path: str) -> str:
    """Reads and returns text content from a given file."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read().strip()
    except FileNotFoundError:
        print(f"Error: {file_path} not found.")
        return ""

def add_grid_and_numbers(image: Image.Image) -> Image.Image:
    """
    Overlays a grid with numbered cells on the given image.
    """
    img_copy = image.copy()
    draw = ImageDraw.Draw(img_copy)
    width, height = image.size
    cell_width = width // SCREENSHOT_GRID_DIVISION_NUM
    cell_height = height // SCREENSHOT_GRID_DIVISION_NUM

    # Load font for cell numbers (using default font)
    font = ImageFont.load_default()

    # Draw vertical grid lines
    for i in range(1, SCREENSHOT_GRID_DIVISION_NUM):
        x = i * cell_width
        draw.line([(x, 0), (x, height)], fill='green', width=SCREENSHOT_GRID_LINE_WIDTH)

    # Draw horizontal grid lines
    for i in range(1, SCREENSHOT_GRID_DIVISION_NUM):
        y = i * cell_height
        draw.line([(0, y), (width, y)], fill='green', width=SCREENSHOT_GRID_LINE_WIDTH)

    # Draw numbers centered in each cell
    for i in range(SCREENSHOT_GRID_DIVISION_NUM):
        for j in range(SCREENSHOT_GRID_DIVISION_NUM):
            number = i * SCREENSHOT_GRID_DIVISION_NUM + j + 1
            text = str(number)
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = j * cell_width + (cell_width - text_width) // 2
            y = i * cell_height + (cell_height - text_height) // 2
            draw.text((x, y), text, fill='green', font=font)

    return img_copy

def encode_image_to_base64(image: Image.Image) -> str:
    """
    Converts a PIL Image to a base64-encoded PNG string.
    """
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def crop_to_cell(image: Image.Image, cell_number: int, output_size: tuple = None) -> Image.Image:
    """
    Crops the image to a specified cell (using a grid overlay).
    """
    width, height = image.size
    cell_width = width // SCREENSHOT_GRID_DIVISION_NUM
    cell_height = height // SCREENSHOT_GRID_DIVISION_NUM

    index = cell_number - 1
    row = index // SCREENSHOT_GRID_DIVISION_NUM
    col = index % SCREENSHOT_GRID_DIVISION_NUM

    left = col * cell_width
    upper = row * cell_height
    right = left + cell_width
    lower = upper + cell_height

    cropped = image.crop((left, upper, right, lower))
    if output_size is not None:
        cropped = cropped.resize(output_size, Image.LANCZOS)
    return cropped
