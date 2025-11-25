# restaurants/groq_menu_extractor.py

import base64
import json
import os
from pathlib import Path

from django.conf import settings
from groq import Groq


def convert_pdf_to_image(pdf_path: str) -> str | None:
    """
    Convert first page of a PDF to PNG and return the image path.
    """
    try:
        from pdf2image import convert_from_path
    except ImportError:
        print("[GroqExtractor] pdf2image not installed. Run: pip install pdf2image")
        return None

    try:
        print(f"[GroqExtractor] Converting PDF to image: {pdf_path}")
        images = convert_from_path(pdf_path, first_page=1, last_page=1, dpi=300)

        pdf_dir = os.path.dirname(pdf_path) or "."
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        image_path = os.path.join(pdf_dir, f"{pdf_name}_converted.png")

        images[0].save(image_path, "PNG")
        print(f"[GroqExtractor] Saved image as: {image_path}")
        return image_path
    except Exception as e:
        print(f"[GroqExtractor] Error converting PDF: {e}")
        return None


def extract_menu_to_json_from_image(image_path: str) -> dict | None:
    """
    Call Groq Vision model on the given image and return parsed JSON.
    """
    api_key = getattr(settings, "GROQ_API_KEY", None)
    if not api_key:
        raise ValueError("GROQ_API_KEY not configured in Django settings.")

    client = Groq(api_key=api_key)

    with open(image_path, "rb") as file:
        file_data = base64.b64encode(file.read()).decode("utf-8")

    prompt = """Extract all menu items from this restaurant menu image and return ONLY a valid JSON object.

Structure the JSON like this:
{
  "restaurant_name": "string or null",
  "phone": "string or null",
  "categories": [
    {
      "category": "string",
      "items": [
        {"name": "string", "price": number}
      ]
    }
  ]
}

Rules:
1. Extract all items with exact names and prices.
2. Group items by category headers.
3. Prices must be numbers only.
4. No explanations. Only JSON.
"""

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{file_data}"
                            },
                        },
                    ],
                }
            ],
            model="meta-llama/llama-4-maverick-17b-128e-instruct",
            temperature=0.1,
            max_tokens=4096,
        )

        response_text = chat_completion.choices[0].message.content.strip()

        # Strip ```json ... ``` wrappers if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]

        menu_data = json.loads(response_text)
        return menu_data

    except json.JSONDecodeError as e:
        print(f"[GroqExtractor] JSON Parse Error: {e}")
        print("Raw Response:")
        print(response_text)
        return None
    except Exception as e:
        print(f"[GroqExtractor] API Error: {e}")
        return None


def extract_and_save_menu_pdf_to_json(pdf_path: str, output_json_path: str) -> dict | None:
    """
    Helper that:
    - converts PDF → image
    - calls Groq Vision → JSON
    - saves JSON to output_json_path
    - returns the menu_data dict
    """
    # 1) PDF → image
    if pdf_path.lower().endswith(".pdf"):
        image_path = convert_pdf_to_image(pdf_path)
        if not image_path:
            print("[GroqExtractor] PDF to image conversion failed.")
            return None
    else:
        image_path = pdf_path

    # 2) Image → JSON via Groq
    menu_data = extract_menu_to_json_from_image(image_path)
    if not menu_data:
        print("[GroqExtractor] Failed to extract menu data from image.")
        return None

    # 3) Save JSON
    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(menu_data, f, indent=2, ensure_ascii=False)

    print(f"[GroqExtractor] Saved JSON to {output_json_path}")
    return menu_data
