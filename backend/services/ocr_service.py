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
        prompt = (
            "Read the food label in this image and extract the list of ingredients. "
            "Output only the ingredient names. Do not transcribe the entire label verbatim."
        )
        
        response = model.generate_content([prompt, image])
        
        try:
            text = response.text.strip()
        except ValueError as e:
            if response.candidates and getattr(response.candidates[0], 'finish_reason', None) == 4:
                raise RuntimeError("The image text triggered copyright filters. Please type the ingredients manually.")
            raise RuntimeError(f"Failed to read response: {e}")

        if not text:
            logger.warning("OCR returned empty text.")
            return ""

        logger.info(f"OCR extracted {len(text)} characters.")
        return text

    except RuntimeError as e:
        logger.error(f"OCR failed: {e}")
        raise e
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        raise RuntimeError(f"Could not extract text from image: {e}")


async def extract_text_from_base64(b64_string: str) -> str:
    """Extract text from a base64-encoded image."""
    image_bytes = base64.b64decode(b64_string)
    return await extract_text_from_image(image_bytes)
