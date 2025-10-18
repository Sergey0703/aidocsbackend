#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR Enhancer for Docling Output
Replaces <!-- image --> placeholders with EasyOCR-extracted text
"""

import re
import logging
from pathlib import Path
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)


class OCREnhancer:
    """
    Enhances Docling markdown output by replacing image placeholders with OCR text
    """

    def __init__(self, use_gpu: bool = False):
        """
        Initialize OCR enhancer

        Args:
            use_gpu: Whether to use GPU for OCR (faster but requires CUDA)
        """
        self.use_gpu = use_gpu
        self.reader = None
        self._initialized = False

    def _initialize_ocr(self):
        """Lazy initialization of EasyOCR (only when needed)"""
        if self._initialized:
            return

        try:
            import easyocr
            logger.info("Initializing EasyOCR...")
            self.reader = easyocr.Reader(['en'], gpu=self.use_gpu)
            self._initialized = True
            logger.info("✅ EasyOCR initialized successfully")
        except ImportError:
            logger.error("EasyOCR not installed. Run: pip install easyocr")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR: {e}")
            raise

    def has_image_placeholders(self, markdown_text: str) -> bool:
        """
        Check if markdown contains <!-- image --> placeholders

        Args:
            markdown_text: Markdown content

        Returns:
            True if placeholders found
        """
        return '<!-- image -->' in markdown_text

    def extract_images_from_pdf(self, pdf_path: str) -> List[Tuple[int, object]]:
        """
        Extract all images from PDF pages

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of (page_number, image) tuples
        """
        try:
            import fitz  # PyMuPDF

            images = []
            doc = fitz.open(pdf_path)

            for page_num in range(len(doc)):
                page = doc[page_num]

                # Render page as image at 300 DPI
                zoom = 300 / 72
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)

                images.append((page_num, pix))

            doc.close()
            logger.info(f"Extracted {len(images)} page images from PDF")
            return images

        except Exception as e:
            logger.error(f"Failed to extract images from PDF: {e}")
            return []

    def ocr_image(self, image_pix) -> str:
        """
        Perform OCR on a PyMuPDF pixmap

        Args:
            image_pix: PyMuPDF Pixmap object

        Returns:
            Extracted text
        """
        if not self._initialized:
            self._initialize_ocr()

        try:
            # Save pixmap to temporary file
            import tempfile
            import os
            import time

            # Create temp file
            fd, tmp_path = tempfile.mkstemp(suffix='.png')
            os.close(fd)  # Close file descriptor immediately

            # Save image
            image_pix.save(tmp_path)

            # Run OCR
            result = self.reader.readtext(tmp_path)

            # Extract text lines
            text_lines = []
            for (bbox, text, confidence) in result:
                if confidence > 0.5:  # Filter low-confidence results
                    text_lines.append(text)

            extracted_text = '\n'.join(text_lines)
            logger.debug(f"OCR extracted {len(text_lines)} lines")

            # Clean up temp file (delayed for Windows)
            try:
                time.sleep(0.1)  # Small delay for Windows file handles
                os.unlink(tmp_path)
            except Exception as cleanup_error:
                logger.debug(f"Could not delete temp file {tmp_path}: {cleanup_error}")
                # Not critical - temp files will be cleaned eventually

            return extracted_text

        except Exception as e:
            logger.error(f"OCR failed: {e}")
            import traceback
            traceback.print_exc()
            return ""

    def enhance_markdown(self, markdown_text: str, pdf_path: str) -> Tuple[str, dict]:
        """
        Enhance markdown by replacing <!-- image --> with OCR text

        Args:
            markdown_text: Original Docling markdown output
            pdf_path: Path to source PDF file

        Returns:
            Tuple of (enhanced_markdown, stats)
        """
        stats = {
            'placeholders_found': 0,
            'placeholders_replaced': 0,
            'ocr_chars_added': 0,
            'pages_processed': 0
        }

        # Check if enhancement needed
        if not self.has_image_placeholders(markdown_text):
            logger.info("No image placeholders found - no OCR enhancement needed")
            return markdown_text, stats

        # Count placeholders
        placeholders = markdown_text.count('<!-- image -->')
        stats['placeholders_found'] = placeholders

        logger.info(f"Found {placeholders} image placeholder(s) - starting OCR enhancement...")

        # Extract images from PDF
        images = self.extract_images_from_pdf(pdf_path)
        if not images:
            logger.warning("No images extracted from PDF")
            return markdown_text, stats

        stats['pages_processed'] = len(images)

        # Process each image
        enhanced_text = markdown_text

        for page_num, image_pix in images:
            logger.info(f"Processing page {page_num + 1}/{len(images)}...")

            # Perform OCR
            ocr_text = self.ocr_image(image_pix)

            if ocr_text:
                # Replace first occurrence of <!-- image -->
                enhanced_text = enhanced_text.replace(
                    '<!-- image -->',
                    f'\n{ocr_text}\n',
                    1  # Replace only first occurrence
                )
                stats['placeholders_replaced'] += 1
                stats['ocr_chars_added'] += len(ocr_text)
                logger.info(f"✅ Replaced placeholder with {len(ocr_text)} chars of OCR text")
            else:
                logger.warning(f"⚠️ OCR returned no text for page {page_num + 1}")

        logger.info(f"Enhancement complete: {stats['placeholders_replaced']}/{stats['placeholders_found']} placeholders replaced")

        return enhanced_text, stats

    def process_file(self, markdown_path: str, pdf_path: str, output_path: Optional[str] = None) -> bool:
        """
        Process a markdown file and enhance it with OCR

        Args:
            markdown_path: Path to Docling-generated markdown
            pdf_path: Path to source PDF
            output_path: Path to save enhanced markdown (defaults to overwriting input)

        Returns:
            True if successful
        """
        try:
            # Read markdown
            with open(markdown_path, 'r', encoding='utf-8') as f:
                markdown_text = f.read()

            # Enhance
            enhanced_text, stats = self.enhance_markdown(markdown_text, pdf_path)

            # Save
            if output_path is None:
                output_path = markdown_path

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(enhanced_text)

            logger.info(f"✅ Saved enhanced markdown to {output_path}")
            logger.info(f"   Stats: {stats}")

            return True

        except Exception as e:
            logger.error(f"Failed to process file: {e}")
            return False


def create_ocr_enhancer(use_gpu: bool = False) -> OCREnhancer:
    """
    Factory function to create OCR enhancer

    Args:
        use_gpu: Whether to use GPU acceleration

    Returns:
        OCREnhancer instance
    """
    return OCREnhancer(use_gpu=use_gpu)


# Example usage
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 3:
        print("Usage: python ocr_enhancer.py <markdown_file> <pdf_file>")
        sys.exit(1)

    markdown_file = sys.argv[1]
    pdf_file = sys.argv[2]

    enhancer = create_ocr_enhancer()
    success = enhancer.process_file(markdown_file, pdf_file)

    if success:
        print("✅ Enhancement successful!")
    else:
        print("❌ Enhancement failed")
        sys.exit(1)
