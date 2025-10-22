#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gemini Vision OCR Engine
Uses Google Gemini 1.5 Flash for high-quality image-to-text extraction
"""

import logging
import base64
from pathlib import Path
from typing import Optional, Dict, Any
import os

logger = logging.getLogger(__name__)


class GeminiVisionOCR:
    """
    OCR engine using Google Gemini 1.5 Flash Vision
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-1.5-flash"):
        """
        Initialize Gemini Vision OCR

        Args:
            api_key: Google API key (if None, will read from env)
            model: Gemini model to use (default: gemini-1.5-flash)
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        self.model_name = model
        self.client = None
        self._initialized = False

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")

    def _initialize(self):
        """Lazy initialization of Gemini client"""
        if self._initialized:
            return

        try:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(self.model_name)
            self._initialized = True

            logger.info(f"[+] Gemini Vision OCR initialized (model: {self.model_name})")

        except ImportError:
            logger.error("google-generativeai not installed. Run: pip install google-generativeai")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Gemini Vision: {e}")
            raise

    def _prepare_prompt(self, extraction_type: str = 'markdown') -> str:
        """
        Prepare extraction prompt

        Args:
            extraction_type: Type of extraction (markdown, text, structured)

        Returns:
            Prompt string
        """
        if extraction_type == 'markdown':
            return """
Extract ALL text from this document image.

Requirements:
- Preserve the original structure and formatting
- Maintain the order of text as it appears
- Keep all headers, labels, and values together
- Output as clean, readable text
- For forms/certificates: preserve field names and their values
- Do NOT add any commentary or explanations
- Do NOT translate text - keep original language

Focus on accuracy and completeness.
"""
        elif extraction_type == 'structured':
            return """
Extract ALL text from this document image and structure it logically.

Requirements:
- Identify field names and their values
- Preserve hierarchical structure
- Keep related information together
- Output as structured text with clear sections
- Do NOT add commentary
- Maintain original language

Example format:
Field Name: Value
Another Field: Another Value
"""
        else:  # text
            return """
Extract ALL visible text from this image exactly as it appears.
Do not add any commentary or explanations.
Output only the extracted text.
"""

    def extract_from_image_file(
        self,
        image_path: str,
        extraction_type: str = 'markdown',
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """
        Extract text from image file

        Args:
            image_path: Path to image file
            extraction_type: Type of extraction
            max_retries: Maximum retry attempts

        Returns:
            Dict with 'text', 'confidence', 'method', 'error' keys
        """
        if not self._initialized:
            self._initialize()

        try:
            from PIL import Image

            # Load image
            image = Image.open(image_path)

            # Prepare prompt
            prompt = self._prepare_prompt(extraction_type)

            # Call Gemini Vision API
            logger.debug(f"Sending image to Gemini Vision API...")
            response = self.client.generate_content([prompt, image])

            # Extract text
            if response and response.text:
                extracted_text = response.text.strip()

                # Calculate pseudo-confidence (Gemini doesn't provide confidence scores)
                # We use text length and presence as heuristics
                if len(extracted_text) > 50:
                    confidence = 0.95  # High confidence for substantial text
                elif len(extracted_text) > 20:
                    confidence = 0.85
                else:
                    confidence = 0.70

                logger.info(f"[+] Gemini Vision extracted {len(extracted_text)} chars")

                return {
                    'text': extracted_text,
                    'confidence': confidence,
                    'method': 'gemini_vision',
                    'model': self.model_name,
                    'chars_extracted': len(extracted_text),
                    'error': None
                }
            else:
                logger.warning("Gemini Vision returned empty response")
                return {
                    'text': '',
                    'confidence': 0.0,
                    'method': 'gemini_vision',
                    'error': 'Empty response from API'
                }

        except Exception as e:
            logger.error(f"Gemini Vision OCR failed: {e}")
            return {
                'text': '',
                'confidence': 0.0,
                'method': 'gemini_vision',
                'error': str(e)
            }

    def extract_from_pixmap(
        self,
        pixmap,
        extraction_type: str = 'markdown'
    ) -> Dict[str, Any]:
        """
        Extract text from PyMuPDF pixmap

        Args:
            pixmap: PyMuPDF Pixmap object
            extraction_type: Type of extraction

        Returns:
            Dict with extraction results
        """
        import tempfile
        import os

        # Save pixmap to temp file
        fd, tmp_path = tempfile.mkstemp(suffix='.png')
        os.close(fd)

        try:
            pixmap.save(tmp_path)
            result = self.extract_from_image_file(tmp_path, extraction_type)
            return result

        finally:
            # Cleanup
            try:
                os.unlink(tmp_path)
            except:
                pass

    def get_daily_limit_remaining(self) -> Optional[int]:
        """
        Get remaining daily API quota (if available)

        Returns:
            Number of requests remaining, or None if unavailable
        """
        # Note: Gemini API doesn't expose quota info programmatically
        # This would need to be tracked separately
        return None


def create_gemini_vision_ocr(
    api_key: Optional[str] = None,
    model: str = "gemini-1.5-flash"
) -> GeminiVisionOCR:
    """
    Factory function to create Gemini Vision OCR instance

    Args:
        api_key: Google API key
        model: Gemini model name

    Returns:
        GeminiVisionOCR instance
    """
    return GeminiVisionOCR(api_key=api_key, model=model)


# Example usage
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python gemini_vision_ocr.py <image_file>")
        sys.exit(1)

    image_file = sys.argv[1]

    ocr = create_gemini_vision_ocr()
    result = ocr.extract_from_image_file(image_file)

    print("\n" + "="*70)
    print("GEMINI VISION OCR RESULT")
    print("="*70)
    print(f"Confidence: {result['confidence']:.2%}")
    print(f"Method: {result['method']}")
    print(f"Chars extracted: {result.get('chars_extracted', 0)}")
    print("\n--- Extracted Text ---")
    print(result['text'])
    print("="*70)
