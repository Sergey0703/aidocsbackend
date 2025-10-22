#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR Enhancer for Docling Output
Replaces <!-- image --> placeholders with EasyOCR-extracted text
"""

import re
import logging
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

logger = logging.getLogger(__name__)


class OCREnhancer:
    """
    Enhances Docling markdown output by replacing image placeholders with OCR text
    Supports multiple OCR engines with fallback strategy
    """

    def __init__(
        self,
        use_gpu: bool = False,
        strategy: str = 'fallback',
        fallback_threshold: float = 0.70
    ):
        """
        Initialize OCR enhancer

        Args:
            use_gpu: Whether to use GPU for EasyOCR (faster but requires CUDA)
            strategy: OCR strategy ('easyocr', 'gemini', 'fallback', 'ensemble')
            fallback_threshold: Confidence threshold to trigger Gemini fallback
        """
        self.use_gpu = use_gpu
        self.strategy = strategy
        self.fallback_threshold = fallback_threshold

        # OCR engines (lazy initialization)
        self.easyocr_reader = None
        self.gemini_ocr = None
        self._easyocr_initialized = False
        self._gemini_initialized = False

        # Statistics
        self.stats = {
            'easyocr_used': 0,
            'gemini_used': 0,
            'fallback_triggered': 0
        }

    def _initialize_easyocr(self):
        """Lazy initialization of EasyOCR"""
        if self._easyocr_initialized:
            return

        try:
            import easyocr
            logger.info("Initializing EasyOCR...")
            self.easyocr_reader = easyocr.Reader(['en'], gpu=self.use_gpu)
            self._easyocr_initialized = True
            logger.info("[+] EasyOCR initialized successfully")
        except ImportError:
            logger.error("EasyOCR not installed. Run: pip install easyocr")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR: {e}")
            raise

    def _initialize_gemini(self):
        """Lazy initialization of Gemini Vision OCR"""
        if self._gemini_initialized:
            return

        try:
            from .gemini_vision_ocr import create_gemini_vision_ocr
            logger.info("Initializing Gemini Vision OCR...")
            self.gemini_ocr = create_gemini_vision_ocr()
            self._gemini_initialized = True
            logger.info("[+] Gemini Vision OCR initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini Vision: {e}")
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

    def _ocr_with_easyocr(self, image_pix) -> Dict[str, Any]:
        """OCR using EasyOCR"""
        if not self._easyocr_initialized:
            self._initialize_easyocr()

        try:
            import tempfile
            import os
            import time

            # Save to temp file
            fd, tmp_path = tempfile.mkstemp(suffix='.png')
            os.close(fd)
            image_pix.save(tmp_path)

            # Run EasyOCR
            result = self.easyocr_reader.readtext(tmp_path)

            # Extract text lines
            text_lines = []
            confidences = []
            for (bbox, text, confidence) in result:
                if confidence > 0.5:
                    text_lines.append(text)
                    confidences.append(confidence)

            extracted_text = '\n'.join(text_lines)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            # Cleanup
            try:
                time.sleep(0.1)
                os.unlink(tmp_path)
            except:
                pass

            return {
                'text': extracted_text,
                'confidence': avg_confidence,
                'method': 'easyocr',
                'lines': len(text_lines)
            }

        except Exception as e:
            logger.error(f"EasyOCR failed: {e}")
            return {
                'text': '',
                'confidence': 0.0,
                'method': 'easyocr',
                'error': str(e)
            }

    def _ocr_with_gemini(self, image_pix) -> Dict[str, Any]:
        """OCR using Gemini Vision"""
        if not self._gemini_initialized:
            self._initialize_gemini()

        try:
            result = self.gemini_ocr.extract_from_pixmap(image_pix)
            return result

        except Exception as e:
            logger.error(f"Gemini Vision failed: {e}")
            return {
                'text': '',
                'confidence': 0.0,
                'method': 'gemini_vision',
                'error': str(e)
            }

    def ocr_image(self, image_pix) -> str:
        """
        Perform OCR on a PyMuPDF pixmap using configured strategy

        Args:
            image_pix: PyMuPDF Pixmap object

        Returns:
            Extracted text
        """
        if self.strategy == 'easyocr':
            # EasyOCR only
            result = self._ocr_with_easyocr(image_pix)
            self.stats['easyocr_used'] += 1
            return result['text']

        elif self.strategy == 'gemini':
            # Gemini only
            result = self._ocr_with_gemini(image_pix)
            self.stats['gemini_used'] += 1
            return result['text']

        elif self.strategy == 'fallback':
            # Try EasyOCR first, fallback to Gemini if confidence low
            easy_result = self._ocr_with_easyocr(image_pix)
            self.stats['easyocr_used'] += 1

            if easy_result['confidence'] >= self.fallback_threshold:
                # EasyOCR confidence is good
                logger.info(f"[+] EasyOCR succeeded (confidence: {easy_result['confidence']:.2%})")
                return easy_result['text']
            else:
                # Fallback to Gemini
                logger.warning(f"[!]  EasyOCR low confidence ({easy_result['confidence']:.2%}), trying Gemini Vision...")
                self.stats['fallback_triggered'] += 1

                gemini_result = self._ocr_with_gemini(image_pix)
                self.stats['gemini_used'] += 1

                if gemini_result['confidence'] > easy_result['confidence']:
                    logger.info(f"[+] Gemini Vision better (confidence: {gemini_result['confidence']:.2%})")
                    return gemini_result['text']
                else:
                    logger.info(f"Using EasyOCR result despite low confidence")
                    return easy_result['text']

        elif self.strategy == 'ensemble':
            # Run both and compare
            easy_result = self._ocr_with_easyocr(image_pix)
            gemini_result = self._ocr_with_gemini(image_pix)

            self.stats['easyocr_used'] += 1
            self.stats['gemini_used'] += 1

            # Choose best result
            if gemini_result['confidence'] > easy_result['confidence']:
                logger.info(f"Ensemble: Using Gemini ({gemini_result['confidence']:.2%} vs {easy_result['confidence']:.2%})")
                return gemini_result['text']
            else:
                logger.info(f"Ensemble: Using EasyOCR ({easy_result['confidence']:.2%} vs {gemini_result['confidence']:.2%})")
                return easy_result['text']

        else:
            raise ValueError(f"Unknown OCR strategy: {self.strategy}")

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
                logger.info(f"[+] Replaced placeholder with {len(ocr_text)} chars of OCR text")
            else:
                logger.warning(f"[!] OCR returned no text for page {page_num + 1}")

        logger.info(f"Enhancement complete: {stats['placeholders_replaced']}/{stats['placeholders_found']} placeholders replaced")

        # Add OCR engine usage stats
        stats['easyocr_used'] = self.stats.get('easyocr_used', 0)
        stats['gemini_used'] = self.stats.get('gemini_used', 0)
        stats['fallback_triggered'] = self.stats.get('fallback_triggered', 0)

        return enhanced_text, stats

    def enhance_docling_document(self, docling_doc, pdf_path: str) -> Tuple[Any, dict]:
        """
        Enhance DoclingDocument by adding OCR text to picture elements

        Args:
            docling_doc: DoclingDocument instance
            pdf_path: Path to source PDF file

        Returns:
            Tuple of (enhanced_docling_doc, stats)
        """
        from docling_core.types.doc import TextItem, RefItem

        stats = {
            'placeholders_found': 0,
            'placeholders_replaced': 0,
            'ocr_chars_added': 0,
            'pages_processed': 0,
            'easyocr_used': 0,
            'gemini_used': 0,
            'fallback_triggered': 0
        }

        # Check if document has pictures
        if not docling_doc.pictures:
            logger.info("No pictures found - no OCR enhancement needed for DoclingDocument")
            return docling_doc, stats

        logger.info(f"Found {len(docling_doc.pictures)} picture(s) - starting OCR enhancement...")

        # Extract images from PDF
        images = self.extract_images_from_pdf(pdf_path)
        if not images:
            logger.warning("No images extracted from PDF")
            return docling_doc, stats

        stats['pages_processed'] = len(images)

        # Process each image and add OCR text to document
        for page_num, image_pix in images:
            logger.info(f"Processing page {page_num + 1}/{len(images)}...")

            # Perform OCR
            ocr_text = self.ocr_image(image_pix)

            if ocr_text:
                # Create new text item with OCR content
                # IMPORTANT: Add to body (not picture) so HybridChunker can see it
                new_text_id = len(docling_doc.texts)
                ocr_text_item = TextItem(
                    self_ref=f"#/texts/{new_text_id}",
                    parent=RefItem(cref="#/body"),  # Add to body, not picture!
                    children=[],
                    label="text",
                    text=ocr_text,
                    orig=ocr_text
                )

                # Add to document
                docling_doc.texts.append(ocr_text_item)

                # Add reference to body's children (so it's visible to HybridChunker)
                docling_doc.body.children.append(RefItem(cref=f"#/texts/{new_text_id}"))

                stats['placeholders_replaced'] += 1
                stats['ocr_chars_added'] += len(ocr_text)
                logger.info(f"[+] Added {len(ocr_text)} chars of OCR text to body (page {page_num + 1})")
            else:
                logger.warning(f"[!] OCR returned no text for page {page_num + 1}")

        logger.info(f"Enhancement complete: Added OCR text to {stats['placeholders_replaced']} picture(s)")

        # Add OCR engine usage stats
        stats['easyocr_used'] = self.stats.get('easyocr_used', 0)
        stats['gemini_used'] = self.stats.get('gemini_used', 0)
        stats['fallback_triggered'] = self.stats.get('fallback_triggered', 0)

        return docling_doc, stats

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

            logger.info(f"[+] Saved enhanced markdown to {output_path}")
            logger.info(f"   Stats: {stats}")

            return True

        except Exception as e:
            logger.error(f"Failed to process file: {e}")
            return False


def create_ocr_enhancer(
    use_gpu: bool = False,
    strategy: str = 'fallback',
    fallback_threshold: float = 0.70
) -> OCREnhancer:
    """
    Factory function to create OCR enhancer

    Args:
        use_gpu: Whether to use GPU acceleration
        strategy: OCR strategy ('easyocr', 'gemini', 'fallback', 'ensemble')
        fallback_threshold: Confidence threshold for Gemini fallback

    Returns:
        OCREnhancer instance
    """
    return OCREnhancer(
        use_gpu=use_gpu,
        strategy=strategy,
        fallback_threshold=fallback_threshold
    )


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
        print("[+] Enhancement successful!")
    else:
        print("[-] Enhancement failed")
        sys.exit(1)
