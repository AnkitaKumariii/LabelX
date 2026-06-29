import os
import base64
import logging
from io import BytesIO
from typing import Optional

from PIL import Image
from services.gemini_service import get_model

logger = logging.getLogger(__name__)


async def extract_text_from_image(image_bytes: bytes) -> str:
    """
    Extract raw text from an uploaded product image using Gemini Vision.
    Returns the raw extracted text, which is then passed to the LLM for parsing.
    """
    try:
        image = Image.open(BytesIO(image_bytes))

        # Convert image to RGB (required by some vision models if transparent/grayscale)
        if image.mode != "RGB":
            image = image.convert("RGB")

        model = get_model()
        prompt = "Extract all text from this image exactly as written. Output nothing else."
        
        response = model.generate_content([prompt, image])
        text = response.text.strip()

        if not text:
            logger.warning("OCR returned empty text.")
            return ""

        logger.info(f"OCR extracted {len(text)} characters.")
        return text

    except Exception as e:
        logger.error(f"OCR failed: {e}")
        raise RuntimeError(f"Could not extract text from image: {e}")


async def extract_text_from_base64(b64_string: str) -> str:
    """Extract text from a base64-encoded image."""
    image_bytes = base64.b64decode(b64_string)
    return await extract_text_from_image(image_bytes)
