#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Document converter module using Docling 2.55.1
Tested and working with basic DocumentConverter initialization
"""

import time
from pathlib import Path
from datetime import datetime

# Docling 2.x imports
from docling.document_converter import DocumentConverter as DoclingConverter
from docling.datamodel.base_models import InputFormat

from .metadata_extractor import MetadataExtractor
from .utils_docling import safe_write_file, format_time
from .ocr_enhancer import create_ocr_enhancer


class DocumentConverter:
    """Converter for documents using Docling 2.x"""
    
    def __init__(
        self,
        config,
        enable_ocr_enhancement=True,
        ocr_strategy='fallback',
        ocr_fallback_threshold=0.70
    ):
        """
        Initialize document converter.

        Args:
            config: DoclingConfig instance.
            enable_ocr_enhancement: Whether to enhance Docling output with OCR (default: True)
            ocr_strategy: OCR strategy ('easyocr', 'gemini', 'fallback', 'ensemble')
            ocr_fallback_threshold: Confidence threshold for Gemini fallback
        """
        self.config = config
        self.metadata_extractor = MetadataExtractor(config)
        self.docling = self._init_docling_converter()
        self.enable_ocr_enhancement = enable_ocr_enhancement
        self.ocr_strategy = ocr_strategy
        self.ocr_fallback_threshold = ocr_fallback_threshold
        self.ocr_enhancer = None  # Lazy initialization
        self.stats = {
            'total_files': 0, 'successful': 0, 'failed': 0, 'total_time': 0,
            'failed_files': [], 'total_batch_time': 0,
            'ocr_enhanced': 0, 'ocr_placeholders_replaced': 0,
            'easyocr_used': 0, 'gemini_used': 0, 'fallback_triggered': 0
        }

        # Print Docling version info
        self._print_docling_info()

        # Print OCR enhancement status
        if self.enable_ocr_enhancement:
            print(f"[*] OCR Enhancement: ENABLED")
            print(f"   Strategy: {ocr_strategy}")
            if ocr_strategy == 'fallback':
                print(f"   Fallback threshold: {ocr_fallback_threshold:.0%}")
        else:
            print("[!] OCR Enhancement: DISABLED")
    
    def _print_docling_info(self):
        """Print Docling version and configuration info"""
        try:
            import docling
            version = getattr(docling, '__version__', 'unknown')
            print(f"[*] Docling version: {version}")

            # Check if pypdfium2 is available
            try:
                import pypdfium2
                pypdfium2_version = getattr(pypdfium2, '__version__', 'unknown')
                print(f"[*] pypdfium2 backend: {pypdfium2_version}")
            except ImportError:
                print("[!] pypdfium2 not installed - PDF processing may be limited")
        except Exception as e:
            print(f"[!] Could not determine Docling version: {e}")
    
    def _init_docling_converter(self):
        """
        Initialize Docling document converter for version 2.55.1

        Uses the EXACT same initialization that worked in test_docling.py
        """
        print("[*] Initializing Docling 2.x converter...")

        try:
            # Use the EXACT same code that worked in the test script
            converter = DoclingConverter(
                allowed_formats=[
                    InputFormat.PDF,
                    InputFormat.DOCX,
                    InputFormat.PPTX,
                    InputFormat.HTML,
                    InputFormat.IMAGE,
                ]
            )

            print("[+] Docling 2.x converter initialized successfully")
            print(f"   Using default OCR and table extraction settings")

            return converter

        except Exception as e:
            print(f"[-] Failed to initialize Docling converter: {e}")
            import traceback
            traceback.print_exc()
            raise

    def _get_ocr_enhancer(self):
        """Lazy initialization of OCR enhancer (only when needed)"""
        if self.ocr_enhancer is None and self.enable_ocr_enhancement:
            print(f"[*] Initializing OCR enhancer (strategy: {self.ocr_strategy})...")
            self.ocr_enhancer = create_ocr_enhancer(
                use_gpu=False,
                strategy=self.ocr_strategy,
                fallback_threshold=self.ocr_fallback_threshold
            )
        return self.ocr_enhancer
    
    def convert_file(self, input_path):
        """
        Convert a single file to markdown using Docling 2.x
        
        Args:
            input_path: Path to input file
            
        Returns:
            tuple: (success: bool, output_path: Path, error_msg: str)
        """
        input_path = Path(input_path)
        
        timestamp = datetime.now().strftime(self.config.TIMESTAMP_FORMAT)
        output_path = self.config.get_output_path(input_path, timestamp)
        
        print(f"\n[*] Converting: {input_path.name}")
        print(f"   -> {output_path.relative_to(self.config.MARKDOWN_OUTPUT_DIR)}")
        
        start_time = time.time()
        
        try:
            # Convert document - EXACT same way as in test script
            result = self.docling.convert(str(input_path))
            
            # Export to markdown
            markdown_content = result.document.export_to_markdown()
            
            # Validate content
            if not markdown_content or len(markdown_content.strip()) < 10:
                raise ValueError("Conversion produced empty or invalid content")
            
            # Write markdown file
            if not safe_write_file(output_path, markdown_content):
                raise IOError(f"Failed to write markdown file to {output_path}")

            # OCR Enhancement: Replace <!-- image --> placeholders with OCR text
            # NOTE: Do OCR BEFORE saving JSON so JSON includes OCR text
            if self.enable_ocr_enhancement and '<!-- image -->' in markdown_content:
                try:
                    print(f"   [*] Image placeholders detected - running OCR enhancement...")
                    enhancer = self._get_ocr_enhancer()

                    enhanced_content, ocr_stats = enhancer.enhance_markdown(
                        markdown_content,
                        str(input_path)
                    )

                    # Update markdown file with enhanced content
                    if ocr_stats['placeholders_replaced'] > 0:
                        if not safe_write_file(output_path, enhanced_content):
                            raise IOError(f"Failed to write enhanced markdown to {output_path}")

                        markdown_content = enhanced_content  # Use enhanced version for metadata
                        self.stats['ocr_enhanced'] += 1
                        self.stats['ocr_placeholders_replaced'] += ocr_stats['placeholders_replaced']

                        # Track which OCR engines were used
                        self.stats['easyocr_used'] += ocr_stats.get('easyocr_used', 0)
                        self.stats['gemini_used'] += ocr_stats.get('gemini_used', 0)
                        self.stats['fallback_triggered'] += ocr_stats.get('fallback_triggered', 0)

                        print(f"   [+] OCR Enhancement: {ocr_stats['placeholders_replaced']} placeholder(s) replaced")
                        print(f"   [*] Added {ocr_stats['ocr_chars_added']:,} chars of OCR text")

                        # Show which engines were used
                        if ocr_stats.get('easyocr_used', 0) > 0:
                            print(f"   [*] EasyOCR: {ocr_stats['easyocr_used']} image(s)")
                        if ocr_stats.get('gemini_used', 0) > 0:
                            print(f"   [*] Gemini Vision: {ocr_stats['gemini_used']} image(s)")

                except Exception as ocr_error:
                    print(f"   [!] OCR enhancement failed: {ocr_error}")
                    print(f"   Continuing with original Docling output...")
                    # Not critical - continue with original markdown

            # Save JSON output for Hybrid Chunking (if enabled)
            # NOTE: Saved AFTER OCR so JSON contains full content
            if self.config.SAVE_JSON_OUTPUT:
                json_output_path = self.config.get_json_output_path(input_path, timestamp)
                if json_output_path:
                    try:
                        # Save DoclingDocument as JSON
                        result.document.save_as_json(str(json_output_path))
                        print(f"   [+] JSON saved: {json_output_path.relative_to(self.config.JSON_OUTPUT_DIR)}")
                    except Exception as json_error:
                        print(f"   [!] Failed to save JSON: {json_error}")
                        # Not critical - continue with conversion

            # Calculate conversion time
            conversion_time = time.time() - start_time

            # Extract and save metadata
            metadata = self.metadata_extractor.extract_metadata(
                input_path=input_path,
                output_path=output_path,
                markdown_content=markdown_content,
                conversion_time=conversion_time,
                docling_result=result
            )
            self.metadata_extractor.save_metadata(input_path, metadata)

            # Success message
            print(f"   [+] Success ({conversion_time:.2f}s)")
            print(f"   [*] Size: {len(markdown_content):,} chars")

            return True, output_path, None

        except Exception as e:
            error_msg = str(e)
            conversion_time = time.time() - start_time

            print(f"   [-] Failed ({conversion_time:.2f}s): {error_msg}")
            
            # Print full traceback for debugging
            import traceback
            traceback.print_exc()
            
            # Save detailed error log
            self._save_failed_conversion_log(input_path, error_msg)
            
            return False, None, error_msg
    
    def convert_batch(self, files_to_process):
        """
        Convert a batch of files, updating stats along the way.
        
        Args:
            files_to_process: List of file paths to convert
            
        Returns:
            dict: Conversion statistics
        """
        if not files_to_process:
            print("⚠️ No files to convert in this batch.")
            return self.get_conversion_stats()
        
        print(f"\n🚀 Starting conversion of {len(files_to_process)} files...")
        batch_start_time = time.time()
        
        successful_in_batch = 0
        failed_in_batch = 0
        total_time_in_batch = 0

        for i, file_path in enumerate(files_to_process, 1):
            self.stats['total_files'] += 1
            print(f"\n[{i}/{len(files_to_process)}]", end=" ")

            file_start_time = time.time()
            success, _, error_msg = self.convert_file(file_path)
            file_conversion_time = time.time() - file_start_time

            if success:
                successful_in_batch += 1
                total_time_in_batch += file_conversion_time
            else:
                failed_in_batch += 1
                self.stats['failed_files'].append({
                    'file': str(file_path), 
                    'error': error_msg, 
                    'timestamp': datetime.now().isoformat()
                })
            
            # Print progress every 5 files
            if i % 5 == 0:
                self._print_progress(i, len(files_to_process), batch_start_time)
        
        # Update cumulative stats
        self.stats['successful'] += successful_in_batch
        self.stats['failed'] += failed_in_batch
        self.stats['total_time'] += total_time_in_batch
        self.stats['total_batch_time'] = time.time() - batch_start_time
        
        # Print final summary
        self._print_final_summary()
        
        return self.get_conversion_stats()
    
    def _save_failed_conversion_log(self, input_path, error_msg):
        """
        Save information about a failed conversion to a log file.
        
        Args:
            input_path: Path to failed input file
            error_msg: Error message
        """
        try:
            failed_dir = Path(self.config.FAILED_CONVERSIONS_DIR)
            failed_dir.mkdir(parents=True, exist_ok=True)
            
            error_log_path = failed_dir / f"{input_path.stem}.error.txt"
            
            # Get Docling version for debugging
            try:
                import docling
                docling_version = docling.__version__
            except:
                docling_version = "unknown"
            
            error_info = (
                f"Docling Conversion Error\n"
                f"{'=' * 60}\n"
                f"File: {input_path}\n"
                f"Error: {error_msg}\n"
                f"Timestamp: {datetime.now().isoformat()}\n"
                f"Docling Version: {docling_version}\n"
                f"{'=' * 60}\n"
            )
            
            safe_write_file(error_log_path, error_info)
            
        except Exception as e:
            print(f"   ⚠️ Could not save failed conversion log: {e}")
    
    def _print_progress(self, current, total, start_time):
        """
        Print conversion progress.
        
        Args:
            current: Current file number
            total: Total files
            start_time: Batch start time
        """
        elapsed = time.time() - start_time
        rate = current / elapsed if elapsed > 0 else 0
        eta = (total - current) / rate if rate > 0 else 0
        
        print(f"\n📊 Progress: {current}/{total} files")
        print(f"   ✅ Successful: {self.stats['successful']}")
        print(f"   ❌ Failed: {self.stats['failed']}")
        print(f"   ⚡ Rate: {rate:.2f} files/sec")
        print(f"   ⏱️ ETA: {format_time(eta)}")
    
    def _print_final_summary(self):
        """Print final conversion summary."""
        print(f"\n" + "=" * 60)
        print(f"✅ BATCH CONVERSION COMPLETED")
        print(f"=" * 60)
        print(f"📊 Results for this batch:")
        print(f"   Total files attempted: {self.stats['total_files']}")
        print(f"   ✅ Successful: {self.stats['successful']}")
        print(f"   ❌ Failed: {self.stats['failed']}")
        
        if self.stats['total_files'] > 0:
            success_rate = (self.stats['successful'] / self.stats['total_files']) * 100
            print(f"   📈 Success rate: {success_rate:.1f}%")
        
        if self.stats.get('total_batch_time'):
            print(f"\n⏱️ Performance for this batch:")
            print(f"   Total time: {format_time(self.stats['total_batch_time'])}")
            if self.stats['successful'] > 0:
                avg_time = self.stats['total_time'] / self.stats['successful']
                print(f"   Average per successful file: {avg_time:.2f}s")
        
        # OCR Enhancement stats
        if self.enable_ocr_enhancement and self.stats.get('ocr_enhanced', 0) > 0:
            print(f"\n🔍 OCR Enhancement:")
            print(f"   Strategy: {self.ocr_strategy}")
            print(f"   Documents enhanced: {self.stats['ocr_enhanced']}")
            print(f"   Image placeholders replaced: {self.stats['ocr_placeholders_replaced']}")

            # Show OCR engine usage
            if self.stats.get('easyocr_used', 0) > 0:
                print(f"   🔤 EasyOCR used: {self.stats['easyocr_used']} image(s)")
            if self.stats.get('gemini_used', 0) > 0:
                print(f"   ✨ Gemini Vision used: {self.stats['gemini_used']} image(s)")
            if self.stats.get('fallback_triggered', 0) > 0:
                print(f"   🔄 Fallback triggered: {self.stats['fallback_triggered']} time(s)")

        if self.stats['failed_files']:
            print(f"\n❌ Failed files (check logs in '{self.config.FAILED_CONVERSIONS_DIR}'):")
            for failed in self.stats['failed_files'][:5]:
                print(f"   - {Path(failed['file']).name}: {failed['error'][:100]}...")
            if len(self.stats['failed_files']) > 5:
                print(f"   ... and {len(self.stats['failed_files']) - 5} more.")

        print(f"=" * 60)
    
    def get_conversion_stats(self):
        """
        Get current conversion statistics.
        
        Returns:
            dict: Copy of statistics dictionary
        """
        return self.stats.copy()


def create_document_converter(config):
    """
    Factory function to create a DocumentConverter instance.
    
    Args:
        config: DoclingConfig instance
        
    Returns:
        DocumentConverter: Initialized converter
    """
    return DocumentConverter(config)