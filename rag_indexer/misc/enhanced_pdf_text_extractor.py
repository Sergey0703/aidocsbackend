#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced PDF text extractor for complex PDF files
Handles graphical PDFs, embedded text, and provides OCR fallback
Specifically designed to extract text from certificates and training materials
"""

import os
import time
import tempfile
from pathlib import Path

# Core PDF processing imports
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

# Utility imports
from file_utils_core import clean_content_from_null_bytes


class EnhancedPDFTextExtractor:
    """Enhanced extractor for complex PDF files with multiple extraction strategies"""
    
    def __init__(self, ocr_processor=None):
        """
        Initialize enhanced PDF text extractor
        
        Args:
            ocr_processor: OCR processor for fallback text extraction
        """
        self.ocr_processor = ocr_processor
        
        # Track extraction attempts and results
        self.extraction_log = []
        
        print("?? Enhanced PDF Text Extractor initialized:")
        print(f"   PyMuPDF: {'?' if PYMUPDF_AVAILABLE else '?'}")
        print(f"   pdfplumber: {'?' if PDFPLUMBER_AVAILABLE else '?'}")
        print(f"   pdf2image: {'?' if PDF2IMAGE_AVAILABLE else '?'}")
        print(f"   OCR processor: {'?' if ocr_processor else '?'}")
    
    def analyze_pdf_structure(self, file_path):
        """
        Deep analysis of PDF structure to understand why text extraction might fail
        
        Args:
            file_path: Path to PDF file
        
        Returns:
            dict: Detailed PDF analysis
        """
        analysis = {
            'file_path': file_path,
            'file_size_mb': os.path.getsize(file_path) / 1024 / 1024,
            'pages': 0,
            'has_extractable_text': False,
            'has_embedded_fonts': False,
            'has_images': False,
            'text_extraction_methods': {},
            'potential_issues': [],
            'recommended_strategy': 'unknown'
        }
        
        if not PYMUPDF_AVAILABLE:
            analysis['potential_issues'].append('PyMuPDF not available')
            return analysis
        
        try:
            doc = fitz.open(file_path)
            analysis['pages'] = len(doc)
            
            # Analyze each page
            total_chars = 0
            image_count = 0
            font_count = 0
            
            for page_num in range(min(3, len(doc))):  # Analyze first 3 pages
                page = doc[page_num]
                
                # Try different text extraction methods
                text_dict = page.get_text("dict")
                text_raw = page.get_text()
                text_blocks = page.get_text("blocks")
                
                analysis['text_extraction_methods'][f'page_{page_num}_dict_chars'] = len(str(text_dict))
                analysis['text_extraction_methods'][f'page_{page_num}_raw_chars'] = len(text_raw)
                analysis['text_extraction_methods'][f'page_{page_num}_blocks_chars'] = len(str(text_blocks))
                
                total_chars += len(text_raw)
                
                # Check for images
                images = page.get_images()
                image_count += len(images)
                
                # Check for fonts
                fonts = page.get_fonts()
                font_count += len(fonts)
                
                # Analyze text structure
                if text_dict and 'blocks' in text_dict:
                    for block in text_dict['blocks']:
                        if 'lines' in block:
                            for line in block['lines']:
                                if 'spans' in line:
                                    for span in line['spans']:
                                        if 'font' in span:
                                            analysis['has_embedded_fonts'] = True
            
            doc.close()
            
            # Determine characteristics
            analysis['has_extractable_text'] = total_chars > 50
            analysis['has_images'] = image_count > 0
            analysis['average_chars_per_page'] = total_chars / max(analysis['pages'], 1)
            
            # Identify potential issues
            if not analysis['has_extractable_text']:
                analysis['potential_issues'].append('No extractable text found')
            
            if analysis['has_images'] and not analysis['has_extractable_text']:
                analysis['potential_issues'].append('Images present but no text - likely scanned/graphic PDF')
            
            if analysis['average_chars_per_page'] < 100:
                analysis['potential_issues'].append('Very low text density - may be graphic-heavy')
            
            if not analysis['has_embedded_fonts']:
                analysis['potential_issues'].append('No embedded fonts detected')
            
            # Recommend strategy
            if not analysis['has_extractable_text'] and analysis['has_images']:
                analysis['recommended_strategy'] = 'ocr_required'
            elif analysis['average_chars_per_page'] < 200:
                analysis['recommended_strategy'] = 'hybrid_with_ocr'
            elif analysis['has_extractable_text']:
                analysis['recommended_strategy'] = 'standard_extraction'
            else:
                analysis['recommended_strategy'] = 'manual_investigation'
            
        except Exception as e:
            analysis['potential_issues'].append(f'Analysis error: {str(e)}')
        
        return analysis
    
    def extract_text_method_1_basic(self, file_path):
        """
        Method 1: Basic PyMuPDF text extraction
        
        Args:
            file_path: Path to PDF file
        
        Returns:
            tuple: (text, method_info)
        """
        method_info = {'method': 'pymupdf_basic', 'success': False, 'chars': 0}
        
        if not PYMUPDF_AVAILABLE:
            method_info['error'] = 'PyMuPDF not available'
            return "", method_info
        
        try:
            doc = fitz.open(file_path)
            text_parts = []
            
            for page in doc:
                text = page.get_text()
                if text.strip():
                    text_parts.append(text.strip())
            
            doc.close()
            
            full_text = '\n\n'.join(text_parts)
            method_info['chars'] = len(full_text)
            method_info['success'] = len(full_text) > 20
            
            return full_text, method_info
            
        except Exception as e:
            method_info['error'] = str(e)
            return "", method_info
    
    def extract_text_method_2_detailed(self, file_path):
        """
        Method 2: Detailed PyMuPDF extraction with different modes
        
        Args:
            file_path: Path to PDF file
        
        Returns:
            tuple: (text, method_info)
        """
        method_info = {'method': 'pymupdf_detailed', 'success': False, 'chars': 0}
        
        if not PYMUPDF_AVAILABLE:
            method_info['error'] = 'PyMuPDF not available'
            return "", method_info
        
        try:
            doc = fitz.open(file_path)
            text_parts = []
            
            for page in doc:
                # Try multiple extraction modes
                text_modes = [
                    page.get_text("text"),      # Standard text
                    page.get_text("blocks"),    # Text blocks
                    page.get_text("words"),     # Individual words
                    page.get_text("dict")       # Dictionary format
                ]
                
                best_text = ""
                max_chars = 0
                
                # Extract from standard text
                if isinstance(text_modes[0], str) and len(text_modes[0]) > max_chars:
                    best_text = text_modes[0]
                    max_chars = len(best_text)
                
                # Extract from blocks
                if isinstance(text_modes[1], list):
                    blocks_text = ""
                    for block in text_modes[1]:
                        if isinstance(block, tuple) and len(block) > 4:
                            blocks_text += str(block[4]) + " "
                        elif isinstance(block, dict) and 'text' in block:
                            blocks_text += block['text'] + " "
                    
                    if len(blocks_text) > max_chars:
                        best_text = blocks_text
                        max_chars = len(best_text)
                
                # Extract from words
                if isinstance(text_modes[2], list):
                    words_text = " ".join([str(word[4]) for word in text_modes[2] 
                                         if isinstance(word, tuple) and len(word) > 4])
                    if len(words_text) > max_chars:
                        best_text = words_text
                        max_chars = len(best_text)
                
                # Extract from dictionary
                if isinstance(text_modes[3], dict):
                    dict_text = self._extract_from_dict(text_modes[3])
                    if len(dict_text) > max_chars:
                        best_text = dict_text
                
                if best_text.strip():
                    text_parts.append(best_text.strip())
            
            doc.close()
            
            full_text = '\n\n'.join(text_parts)
            method_info['chars'] = len(full_text)
            method_info['success'] = len(full_text) > 20
            
            return full_text, method_info
            
        except Exception as e:
            method_info['error'] = str(e)
            return "", method_info
    
    def extract_text_method_3_pdfplumber(self, file_path):
        """
        Method 3: pdfplumber extraction
        
        Args:
            file_path: Path to PDF file
        
        Returns:
            tuple: (text, method_info)
        """
        method_info = {'method': 'pdfplumber', 'success': False, 'chars': 0}
        
        if not PDFPLUMBER_AVAILABLE:
            method_info['error'] = 'pdfplumber not available'
            return "", method_info
        
        try:
            text_parts = []
            
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    # Try different extraction methods
                    text1 = page.extract_text()
                    text2 = page.extract_text(layout=True)
                    
                    # Use the version with more content
                    best_text = text2 if text2 and len(text2) > len(text1 or "") else text1
                    
                    if best_text and best_text.strip():
                        text_parts.append(best_text.strip())
            
            full_text = '\n\n'.join(text_parts)
            method_info['chars'] = len(full_text)
            method_info['success'] = len(full_text) > 20
            
            return full_text, method_info
            
        except Exception as e:
            method_info['error'] = str(e)
            return "", method_info
    
    def extract_text_method_4_ocr_fallback(self, file_path):
        """
        Method 4: OCR fallback with automatic rotation detection
        Automatically tests all rotation angles and chooses the best result
        
        Args:
            file_path: Path to PDF file
        
        Returns:
            tuple: (text, method_info)
        """
        method_info = {'method': 'ocr_auto_rotation', 'success': False, 'chars': 0}
        
        if not (PDF2IMAGE_AVAILABLE and self.ocr_processor):
            method_info['error'] = 'OCR not available'
            return "", method_info
        
        try:
            # Convert PDF to images with high quality for better OCR
            images = convert_from_path(file_path, dpi=300, fmt='jpeg')
            text_parts = []
            total_rotation_stats = {
                'pages_processed': 0,
                'rotations_applied': 0,
                'quality_improvements': 0,
                'total_tests': 0
            }
            
            for page_num, image in enumerate(images):
                # Save image temporarily
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                    image.save(temp_file.name, 'JPEG')
                    temp_path = temp_file.name
                
                try:
                    print(f"   ?? Processing page {page_num + 1} with auto-rotation...")
                    
                    # Use OCR processor with automatic rotation detection
                    # This will automatically test 0°, 90°, 180°, 270° and choose the best
                    text = self.ocr_processor.extract_text_from_image(temp_path)
                    
                    # Get rotation statistics if available
                    if hasattr(self.ocr_processor, 'rotation_stats'):
                        stats = self.ocr_processor.rotation_stats
                        total_rotation_stats['rotations_applied'] += stats.get('rotations_applied', 0)
                        total_rotation_stats['quality_improvements'] += stats.get('improvements_found', 0)
                        total_rotation_stats['total_tests'] += 1
                    
                    if text and len(text.strip()) > 10:
                        cleaned_text = clean_content_from_null_bytes(text.strip())
                        text_parts.append(cleaned_text)
                        print(f"      ? Extracted {len(cleaned_text)} chars from page {page_num + 1}")
                    else:
                        print(f"      ?? No quality text from page {page_num + 1}")
                    
                    total_rotation_stats['pages_processed'] += 1
                    
                finally:
                    # Clean up temporary file
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
            
            full_text = '\n\n'.join(text_parts)
            method_info['chars'] = len(full_text)
            method_info['success'] = len(full_text) > 20
            method_info['pages_processed'] = len(images)
            method_info['rotation_stats'] = total_rotation_stats
            
            # Add summary of rotation benefits
            if total_rotation_stats['rotations_applied'] > 0:
                method_info['rotation_benefit'] = f"Applied {total_rotation_stats['rotations_applied']} rotations, found {total_rotation_stats['quality_improvements']} improvements"
                print(f"   ?? Rotation summary: {method_info['rotation_benefit']}")
            
            return full_text, method_info
            
        except Exception as e:
            method_info['error'] = str(e)
            return "", method_info
    
    def _extract_from_dict(self, text_dict):
        """
        Extract text from PyMuPDF dictionary format
        
        Args:
            text_dict: Dictionary from get_text("dict")
        
        Returns:
            str: Extracted text
        """
        text_parts = []
        
        try:
            if 'blocks' in text_dict:
                for block in text_dict['blocks']:
                    if 'lines' in block:
                        for line in block['lines']:
                            if 'spans' in line:
                                line_text = ""
                                for span in line['spans']:
                                    if 'text' in span:
                                        line_text += span['text']
                                if line_text.strip():
                                    text_parts.append(line_text.strip())
        except Exception:
            pass
        
        return ' '.join(text_parts)
    
    def extract_text_comprehensive(self, file_path, debug=False):
        """
        Comprehensive text extraction using all available methods with intelligent strategy
        Automatically handles rotation detection and chooses best extraction method
        
        Args:
            file_path: Path to PDF file
            debug: Whether to show debug information
        
        Returns:
            tuple: (best_text, extraction_summary)
        """
        if debug:
            print(f"\n?? Comprehensive extraction: {os.path.basename(file_path)}")
        
        # Analyze PDF structure first
        analysis = self.analyze_pdf_structure(file_path)
        
        if debug:
            print(f"   ?? Analysis: {analysis['pages']} pages, {analysis['file_size_mb']:.1f}MB")
            print(f"   ?? Strategy: {analysis['recommended_strategy']}")
            if analysis['potential_issues']:
                print(f"   ?? Issues: {', '.join(analysis['potential_issues'])}")
        
        # Intelligent method selection based on analysis
        extraction_methods = []
        
        # Always try basic methods first
        extraction_methods.append(self.extract_text_method_1_basic)
        extraction_methods.append(self.extract_text_method_2_detailed)
        
        # Add pdfplumber if available
        if PDFPLUMBER_AVAILABLE:
            extraction_methods.append(self.extract_text_method_3_pdfplumber)
        
        # Smart OCR strategy based on analysis
        if self.ocr_processor and PDF2IMAGE_AVAILABLE:
            if analysis['recommended_strategy'] in ['ocr_required', 'hybrid_with_ocr']:
                # For these cases, try OCR early in the process
                extraction_methods.insert(1, self.extract_text_method_4_ocr_fallback)
                if debug:
                    print("   ?? Auto-rotation OCR prioritized based on PDF analysis")
            else:
                # For normal PDFs, try OCR as fallback
                extraction_methods.append(self.extract_text_method_4_ocr_fallback)
                if debug:
                    print("   ?? Auto-rotation OCR available as fallback")
        
        extraction_results = []
        best_so_far = 0
        
        for i, method in enumerate(extraction_methods):
            start_time = time.time()
            text, method_info = method(file_path)
            method_info['processing_time'] = time.time() - start_time
            
            if debug and method_info['success']:
                rotation_info = ""
                if 'rotation_benefit' in method_info:
                    rotation_info = f" | {method_info['rotation_benefit']}"
                print(f"   ? {method_info['method']}: {method_info['chars']} chars in {method_info['processing_time']:.2f}s{rotation_info}")
                
                # Early termination if we found excellent OCR result
                if method_info['method'] == 'ocr_auto_rotation' and method_info['chars'] > best_so_far * 2:
                    if debug:
                        print(f"      ?? Excellent OCR result found, stopping early")
                    extraction_results.append((text, method_info))
                    break
            elif debug:
                error = method_info.get('error', 'No text extracted')
                print(f"   ? {method_info['method']}: {error}")
            
            extraction_results.append((text, method_info))
            
            # Track best result for early termination logic
            if method_info['success']:
                best_so_far = max(best_so_far, method_info['chars'])
        
        # Find best result
        best_text = ""
        best_method = None
        max_chars = 0
        
        for text, method_info in extraction_results:
            if method_info['success'] and method_info['chars'] > max_chars:
                best_text = text
                best_method = method_info
                max_chars = method_info['chars']
        
        # Clean the best text
        if best_text:
            best_text = clean_content_from_null_bytes(best_text)
        
        # Create summary with rotation information
        extraction_summary = {
            'pdf_analysis': analysis,
            'methods_tried': [info for text, info in extraction_results],
            'best_method': best_method,
            'success': len(best_text) > 20,
            'final_text_length': len(best_text),
            'auto_rotation_used': False,
            'rotation_improvements': 0
        }
        
        # Check if auto-rotation was beneficial
        if best_method and best_method.get('method') == 'ocr_auto_rotation':
            extraction_summary['auto_rotation_used'] = True
            if 'rotation_stats' in best_method:
                rotation_stats = best_method['rotation_stats']
                extraction_summary['rotation_improvements'] = rotation_stats.get('quality_improvements', 0)
        
        if debug:
            if best_text:
                rotation_note = ""
                if extraction_summary['auto_rotation_used']:
                    rotation_note = f" (with {extraction_summary['rotation_improvements']} rotation improvements)"
                print(f"   ?? BEST: {best_method['method']} with {len(best_text)} characters{rotation_note}")
                print(f"   ?? Preview: {best_text[:100]}...")
            else:
                print(f"   ?? FAILED: No method extracted sufficient text")
        
        return best_text, extraction_summary
    
    def test_single_pdf(self, file_path):
        """
        Test extraction on a single PDF with full diagnostics
        
        Args:
            file_path: Path to PDF file
        
        Returns:
            dict: Test results
        """
        print(f"\n?? TESTING: {os.path.basename(file_path)}")
        
        start_time = time.time()
        text, summary = self.extract_text_comprehensive(file_path, debug=True)
        total_time = time.time() - start_time
        
        result = {
            'file_name': os.path.basename(file_path),
            'success': summary['success'],
            'text_length': len(text),
            'word_count': len(text.split()) if text else 0,
            'processing_time': total_time,
            'extraction_summary': summary,
            'text_preview': text[:200] if text else ""
        }
        
        print(f"   ?? RESULT: {result['text_length']} chars, {result['word_count']} words in {total_time:.2f}s")
        if result['success']:
            print(f"   ? SUCCESS with {summary['best_method']['method']}")
        else:
            print(f"   ? FAILED - no method worked")
        
        return result


def test_enhanced_extractor(test_file_path, ocr_processor=None):
    """
    Test the enhanced extractor on a specific file
    
    Args:
        test_file_path: Path to PDF file to test
        ocr_processor: Optional OCR processor
    
    Returns:
        dict: Test results
    """
    extractor = EnhancedPDFTextExtractor(ocr_processor)
    return extractor.test_single_pdf(test_file_path)


if __name__ == "__main__":
    # Test the enhanced extractor
    import sys
    
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        if os.path.exists(test_file):
            print("?? Testing Enhanced PDF Text Extractor")
            result = test_enhanced_extractor(test_file)
            print(f"\nFinal result: {result['success']}")
        else:
            print(f"File not found: {test_file}")
    else:
        print("Usage: python enhanced_pdf_text_extractor.py <pdf_file>")