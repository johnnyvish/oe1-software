import os
import json
from dotenv import load_dotenv
from PIL import Image, ImageGrab
from image_utils import add_grid_and_numbers, encode_image_to_base64, read_prompt_from_file
from openai import OpenAI  # Adjust this import according to your OpenAI package

# Load environment variables from .env file
load_dotenv()

GPT_MAX_TOKENS = 250  # Maximum tokens for GPT

def call_gpt_vision(prompt: str = "Locate the object on the screen.", image: Image.Image = None) -> str:
    """
    Sends an image (with grid overlay) along with a prompt to GPT-4 Vision and returns the response.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("API Key not found. Ensure your .env file contains OPENAI_API_KEY.")

    # If no image is provided, capture a full-screen screenshot.
    if image is None:
        image = ImageGrab.grab()

    # Add grid overlay and encode image
    image_with_grid = add_grid_and_numbers(image)
    base64_image = encode_image_to_base64(image_with_grid)

    client = OpenAI(api_key=api_key)
    instruction_text = read_prompt_from_file("system_instructions.txt")

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": [
                        {"type": "text", "text": instruction_text}
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                    ]
                }
            ],
            max_tokens=GPT_MAX_TOKENS
        )
        return response.choices[0].message.content

    except Exception as e:
        # Return a JSON string with the error message for debugging.
        return json.dumps({"error": str(e)})
