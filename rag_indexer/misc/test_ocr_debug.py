#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced OCR Debug Test Script - English Only
Enhanced testing script for OCR with auto-rotation detection and text quality analysis
Optimized for English language documents only
"""

import os
import sys
import time
from pathlib import Path

# OCR libraries
try:
    import pytesseract
    from PIL import Image, ImageEnhance, ImageFilter
    import cv2
    import numpy as np
    print("? All OCR libraries loaded successfully")
except ImportError as e:
    print(f"? Import error: {e}")
    sys.exit(1)

# Import our enhanced modules
try:
    from ocr_processor import TextQualityAnalyzer, OCRProcessor
    from config import get_config
    print("? Enhanced OCR modules loaded")
except ImportError as e:
    print(f"WARNING: Could not load enhanced modules: {e}")
    print("Running in basic mode...")


def check_tesseract_installation():
    """Check Tesseract installation and capabilities"""
    try:
        version = pytesseract.get_tesseract_version()
        print(f"? Tesseract version: {version}")
        
        languages = pytesseract.get_languages()
        print(f"? Available languages: {languages}")
        
        if 'eng' in languages:
            print("? English language supported")
        else:
            print("?? English language not found")
            
        return True
    except Exception as e:
        print(f"? Tesseract error: {e}")
        return False


def simple_ocr_test(image_path):
    """Simple OCR test without preprocessing"""
    try:
        print(f"\n=== SIMPLE OCR TEST ===")
        print(f"File: {image_path}")
        
        # Check file
        if not os.path.exists(image_path):
            print(f"? File not found: {image_path}")
            return None
            
        # Open image
        image = Image.open(image_path)
        print(f"? Image opened: {image.size}, mode: {image.mode}")
        
        # Simple text extraction
        text = pytesseract.image_to_string(image, lang='eng')
        print(f"?? Extracted text ({len(text)} characters):")
        print("-" * 40)
        print(text[:500] + "..." if len(text) > 500 else text)
        print("-" * 40)
        
        return text
        
    except Exception as e:
        print(f"? Simple OCR error: {e}")
        return None


def advanced_ocr_test(image_path):
    """Advanced OCR test with preprocessing"""
    try:
        print(f"\n=== ADVANCED OCR TEST ===")
        print(f"File: {image_path}")
        
        # Open image
        image = Image.open(image_path)
        print(f"? Original image: {image.size}")
        
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
            print(f"? Converted to RGB")
        
        # Scale small images
        width, height = image.size
        if width < 1000 or height < 1000:
            scale_factor = max(1000/width, 1000/height)
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            image = image.resize((new_width, new_height), Image.LANCZOS)
            print(f"? Scaled to: {new_width}x{new_height}")
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)
        print(f"? Contrast enhanced")
        
        # Enhance sharpness
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2.0)
        print(f"? Sharpness enhanced")
        
        # Convert to grayscale
        image = image.convert('L')
        print(f"? Converted to grayscale")
        
        # Apply filter
        image = image.filter(ImageFilter.MedianFilter(size=3))
        print(f"? Filter applied")
        
        # SAFE OCR configuration (no problematic characters)
        safe_config = r'--oem 3 --psm 6'
        
        print(f"? Using configuration: {safe_config}")
        
        # Extract text
        text = pytesseract.image_to_string(image, lang='eng', config=safe_config)
        
        print(f"?? Extracted text ({len(text)} characters):")
        print("-" * 40)
        print(text[:500] + "..." if len(text) > 500 else text)
        print("-" * 40)
        
        # Quality analysis
        if text.strip():
            letters = sum(c.isalpha() for c in text)
            total_chars = len(text.replace(' ', '').replace('\n', ''))
            quality_score = letters / total_chars if total_chars > 0 else 0
            
            print(f"?? Quality analysis:")
            print(f"   Letters: {letters}")
            print(f"   Total characters: {total_chars}")
            print(f"   Quality: {quality_score:.2f}")
            
            if quality_score > 0.3:
                print(f"? Good quality")
            else:
                print(f"?? Low quality")
        else:
            print(f"?? No text extracted")
        
        return text
        
    except Exception as e:
        print(f"? Advanced OCR error: {e}")
        return None


def test_rotation_detection(image_path):
    """NEW: Test automatic rotation detection"""
    try:
        print(f"\n=== ROTATION DETECTION TEST ===")
        print(f"File: {image_path}")
        
        # Load image
        image = Image.open(image_path)
        
        # Preprocess image (same as advanced test)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        width, height = image.size
        if width < 1000 or height < 1000:
            scale_factor = max(1000/width, 1000/height)
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            image = image.resize((new_width, new_height), Image.LANCZOS)
        
        # Enhance image
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)
        
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2.0)
        
        image = image.convert('L')
        image = image.filter(ImageFilter.MedianFilter(size=3))
        
        # Test all rotations
        rotations = [0, 90, 180, 270]
        results = []
        
        print(f"?? Testing {len(rotations)} rotation angles...")
        
        for angle in rotations:
            print(f"\n   Testing {angle}° rotation:")
            
            # Rotate image if needed
            if angle == 0:
                test_image = image
            else:
                test_image = image.rotate(-angle, expand=True)
            
            # Extract text
            start_time = time.time()
            text = pytesseract.image_to_string(test_image, lang='eng', config=r'--oem 3 --psm 6')
            ocr_time = time.time() - start_time
            
            # Calculate quality score
            letters = sum(c.isalpha() for c in text)
            digits = sum(c.isdigit() for c in text)
            spaces = sum(c.isspace() for c in text)
            total_chars = len(text.replace(' ', '').replace('\n', ''))
            
            quality_score = letters / total_chars if total_chars > 0 else 0.0
            
            # Count English-like words (simple heuristic)
            words = text.split()
            english_like_words = sum(1 for word in words if len(word) > 1 and word.isalpha())
            word_quality = english_like_words / len(words) if words else 0.0
            
            # Combined quality score
            combined_quality = (quality_score * 0.7) + (word_quality * 0.3)
            
            result = {
                'angle': angle,
                'text_length': len(text),
                'letters': letters,
                'quality_score': quality_score,
                'word_quality': word_quality,
                'combined_quality': combined_quality,
                'ocr_time': ocr_time,
                'text_preview': text[:100].replace('\n', ' ').strip()
            }
            
            results.append(result)
            
            print(f"     Length: {len(text)}, Quality: {combined_quality:.2f}, Time: {ocr_time:.2f}s")
            print(f"     Preview: {result['text_preview']}...")
        
        # Find best rotation
        best_result = max(results, key=lambda x: x['combined_quality'])
        best_angle = best_result['angle']
        
        print(f"\n?? BEST ROTATION ANALYSIS:")
        print(f"   Best angle: {best_angle}°")
        print(f"   Best quality: {best_result['combined_quality']:.2f}")
        print(f"   Text length: {best_result['text_length']}")
        print(f"   Letters: {best_result['letters']}")
        
        # Compare with original
        original_result = results[0]  # 0° is always first
        if best_angle != 0:
            improvement = best_result['combined_quality'] - original_result['combined_quality']
            print(f"   Quality improvement: +{improvement:.2f}")
            print(f"   ? Rotation recommended: {best_angle}°")
        else:
            print(f"   ? Original orientation is best")
        
        # Show all results summary
        print(f"\n?? All rotation results:")
        for result in results:
            status = "?? BEST" if result['angle'] == best_angle else ""
            print(f"   {result['angle']:3d}°: Quality {result['combined_quality']:.2f}, "
                  f"Length {result['text_length']:4d} {status}")
        
        return results, best_result
        
    except Exception as e:
        print(f"? Rotation detection error: {e}")
        return [], None


def test_text_quality_analysis(test_texts=None):
    """NEW: Test text quality analyzer"""
    try:
        print(f"\n=== TEXT QUALITY ANALYSIS TEST ===")
        
        # Import quality analyzer if available
        try:
            analyzer = TextQualityAnalyzer('english')
        except NameError:
            print("? TextQualityAnalyzer not available")
            return
        
        # Default test texts if none provided
        if test_texts is None:
            test_texts = [
                "This is a normal English sentence with proper structure and punctuation.",
                "The quick brown fox jumps over the lazy dog. This sentence contains all letters.",
                "aaaaaaaaaaa bbbbbbbb ccccccc",  # Repetitive
                "abc xyz 123 !@# $%^ &*()",  # Low quality symbols
                "Th1s 1s b4d qu4l1ty t3xt w1th numb3rs",  # Numbers in words
                "",  # Empty
                "A",  # Too short
                "Hello world! This is good text with proper English words and structure.",
                "asdfgh qwerty zxcvbn poiuyt",  # Random characters
                "We can analyze the performance metrics to determine the optimal configuration parameters."  # Technical but good
            ]
        
        print(f"?? Testing {len(test_texts)} text samples:")
        
        results = []
        for i, text in enumerate(test_texts, 1):
            print(f"\n   Sample {i}: {text[:50]}{'...' if len(text) > 50 else ''}")
            
            # Analyze quality
            quality_score, detailed_metrics = analyzer.calculate_quality_score(text, min_words=3, max_identical_chars=10)
            
            # Extract key metrics
            if 'structure' in detailed_metrics:
                structure = detailed_metrics['structure']
                letter_ratio = structure['letter_ratio']
                word_count = structure['words']
                avg_word_length = structure['avg_word_length']
            else:
                letter_ratio = 0
                word_count = 0
                avg_word_length = 0
            
            result = {
                'text': text,
                'quality_score': quality_score,
                'letter_ratio': letter_ratio,
                'word_count': word_count,
                'avg_word_length': avg_word_length
            }
            
            results.append(result)
            
            # Show result
            if 'reason' in detailed_metrics:
                print(f"     ? REJECTED: {detailed_metrics['reason']}")
            else:
                status = "? GOOD" if quality_score >= 0.3 else "?? POOR"
                print(f"     {status}: Quality {quality_score:.2f}, Letters {letter_ratio:.2f}, "
                      f"Words {word_count}, Avg word len {avg_word_length:.1f}")
        
        # Summary
        good_quality = [r for r in results if r['quality_score'] >= 0.3]
        print(f"\n?? Quality Analysis Summary:")
        print(f"   Total samples: {len(results)}")
        print(f"   Good quality (=0.3): {len(good_quality)}")
        print(f"   Poor quality: {len(results) - len(good_quality)}")
        print(f"   Success rate: {len(good_quality)/len(results)*100:.1f}%")
        
        return results
        
    except Exception as e:
        print(f"? Text quality analysis error: {e}")
        return []


def test_enhanced_ocr_processor(image_path):
    """NEW: Test the enhanced OCR processor with all features"""
    try:
        print(f"\n=== ENHANCED OCR PROCESSOR TEST ===")
        print(f"File: {image_path}")
        
        # Try to load config
        try:
            config = get_config()
            print("? Configuration loaded")
        except:
            config = None
            print("?? Using default configuration")
        
        # Create enhanced OCR processor
        processor = OCRProcessor(quality_threshold=0.3, batch_size=1, config=config)
        
        if not processor.is_available:
            print("? Enhanced OCR processor not available")
            return None
        
        print(f"? Enhanced OCR processor created")
        print(f"   Auto-rotation: {'?' if processor.auto_rotation else '?'}")
        print(f"   Text quality analysis: {'?' if processor.text_quality_enabled else '?'}")
        print(f"   Quality threshold: {processor.text_quality_min_score:.2f}")
        print(f"   Language: {processor.text_quality_language}")
        
        # Process image
        start_time = time.time()
        document = processor.process_single_image(image_path)
        processing_time = time.time() - start_time
        
        if document:
            print(f"\n? SUCCESS: Document created")
            print(f"   Processing time: {processing_time:.2f}s")
            print(f"   Text length: {len(document.text)} characters")
            print(f"   Quality score: {document.metadata.get('quality_score', 'N/A')}")
            
            # Show metadata info
            if 'ocr_metrics' in document.metadata:
                metrics = document.metadata['ocr_metrics']
                if 'detected_language' in metrics:
                    print(f"   Detected language: {metrics['detected_language']}")
                if 'structure' in metrics:
                    structure = metrics['structure']
                    print(f"   Words: {structure.get('words', 'N/A')}")
                    print(f"   Letter ratio: {structure.get('letter_ratio', 0):.2f}")
            
            # Show rotation info if available
            if 'rotation_info' in document.metadata:
                rotation_info = document.metadata['rotation_info']
                best_angle = rotation_info.get('best_angle', 0)
                if best_angle != 0:
                    print(f"   ?? Applied rotation: {best_angle}°")
                    print(f"   Quality improvement: +{rotation_info.get('quality_improvement', 0):.2f}")
                else:
                    print(f"   ?? No rotation needed")
            
            # Show text preview
            preview = document.text.replace('\n', ' ').strip()
            print(f"\n?? Text preview:")
            print(f"   {preview[:200]}{'...' if len(preview) > 200 else ''}")
            
            return document
            
        else:
            print(f"? FAILED: No document created")
            print(f"   Processing time: {processing_time:.2f}s")
            
            # Try to get failure details
            try:
                text = processor.extract_text_from_image(image_path)
                if text:
                    is_valid, quality_score, metrics = processor.validate_extracted_text(text)
                    print(f"   Text extracted but rejected:")
                    print(f"   Quality score: {quality_score:.2f} (threshold: {processor.text_quality_min_score:.2f})")
                    if 'reason' in metrics:
                        print(f"   Rejection reason: {metrics['reason']}")
                else:
                    print(f"   No text could be extracted")
            except:
                print(f"   Could not determine failure reason")
            
            return None
        
    except Exception as e:
        print(f"? Enhanced OCR processor error: {e}")
        return None


def test_opencv_processing(image_path):
    """Test OpenCV image processing"""
    try:
        print(f"\n=== OPENCV PROCESSING TEST ===")
        
        # Read image with OpenCV
        img = cv2.imread(image_path)
        if img is None:
            print(f"? OpenCV cannot read file")
            return None
            
        print(f"? OpenCV read image: {img.shape}")
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        print(f"? Converted to grayscale")
        
        # Apply Gaussian blur to remove noise
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        print(f"? Blur applied")
        
        # Binarization
        _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        print(f"? Binarization completed")
        
        # Convert back to PIL for OCR
        pil_image = Image.fromarray(thresh)
        
        # OCR with processed image
        text = pytesseract.image_to_string(pil_image, lang='eng', config=r'--oem 3 --psm 6')
        
        print(f"?? Text after OpenCV processing ({len(text)} characters):")
        print("-" * 40)
        print(text[:500] + "..." if len(text) > 500 else text)
        print("-" * 40)
        
        return text
        
    except Exception as e:
        print(f"? OpenCV processing error: {e}")
        return None


def test_different_configs(image_path):
    """Test different OCR configurations"""
    try:
        print(f"\n=== DIFFERENT OCR CONFIGURATIONS TEST ===")
        
        image = Image.open(image_path)
        if image.mode != 'L':
            image = image.convert('L')
        
        configs = [
            ('Default', ''),
            ('OEM 3 PSM 6', '--oem 3 --psm 6'),
            ('OEM 3 PSM 7', '--oem 3 --psm 7'),
            ('OEM 3 PSM 8', '--oem 3 --psm 8'),
            ('OEM 1 PSM 6', '--oem 1 --psm 6'),
            ('OEM 3 PSM 3', '--oem 3 --psm 3'),  # Single text block
        ]
        
        results = []
        
        for name, config in configs:
            try:
                print(f"\n?? Testing: {name} ({config})")
                start_time = time.time()
                text = pytesseract.image_to_string(image, lang='eng', config=config)
                ocr_time = time.time() - start_time
                
                if text.strip():
                    letters = sum(c.isalpha() for c in text)
                    total = len(text.replace(' ', '').replace('\n', ''))
                    quality = letters / total if total > 0 else 0
                    
                    print(f"   Length: {len(text)}, Quality: {quality:.2f}, Time: {ocr_time:.2f}s")
                    print(f"   Preview: {text[:100].replace(chr(10), ' ').strip()}...")
                    
                    results.append((name, len(text), quality, ocr_time, text))
                else:
                    print(f"   ? No text extracted")
                    results.append((name, 0, 0, ocr_time, ""))
                    
            except Exception as e:
                print(f"   ? Error: {e}")
                results.append((name, 0, 0, 0, ""))
        
        # Best results analysis
        if results:
            best_by_quality = max(results, key=lambda x: x[2])  # By quality
            best_by_length = max(results, key=lambda x: x[1])   # By length
            fastest = min([r for r in results if r[1] > 0], key=lambda x: x[3], default=None)  # Fastest with results
            
            print(f"\n?? CONFIGURATION ANALYSIS:")
            print(f"   Best quality: {best_by_quality[0]} (score: {best_by_quality[2]:.2f})")
            print(f"   Most text: {best_by_length[0]} (length: {best_by_length[1]})")
            if fastest:
                print(f"   Fastest: {fastest[0]} (time: {fastest[3]:.2f}s)")
            
            # Recommend best overall configuration
            # Weight quality more than speed
            scored_results = []
            for name, length, quality, time, text in results:
                if length > 0:
                    # Combined score: 70% quality, 20% length, 10% speed
                    speed_score = 1 / (time + 0.1)  # Avoid division by zero
                    combined_score = (quality * 0.7) + (min(length/1000, 1.0) * 0.2) + (min(speed_score, 1.0) * 0.1)
                    scored_results.append((name, combined_score, quality, length, time))
            
            if scored_results:
                best_overall = max(scored_results, key=lambda x: x[1])
                print(f"   ?? RECOMMENDED: {best_overall[0]} (combined score: {best_overall[1]:.2f})")
        
        return results
        
    except Exception as e:
        print(f"? Configuration testing error: {e}")
        return []


def find_test_images(directory="./data/634/2025"):
    """Find test images for OCR testing"""
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']
    images = []
    
    try:
        for root, dirs, files in os.walk(directory):
            for file in files:
                if any(file.lower().endswith(ext) for ext in image_extensions):
                    images.append(os.path.join(root, file))
                    if len(images) >= 10:  # Limit for testing
                        break
            if len(images) >= 10:
                break
                
        return images
    except Exception as e:
        print(f"? Error finding images: {e}")
        return []


def interactive_test_menu():
    """Interactive menu for different tests"""
    while True:
        print(f"\n" + "="*50)
        print("?? ENHANCED OCR DEBUG TEST MENU")
        print("="*50)
        print("1. Basic OCR Test")
        print("2. Advanced OCR Test") 
        print("3. ?? Rotation Detection Test (NEW)")
        print("4. ?? Text Quality Analysis Test (NEW)")
        print("5. ?? Enhanced OCR Processor Test (NEW)")
        print("6. OpenCV Processing Test")
        print("7. OCR Configuration Test")
        print("8. ?? Find and List Test Images")
        print("9. ?? Test Document Image Extraction (NEW)")
        print("0. Exit")
        print("="*50)
        
        choice = input("Select test (0-9): ").strip()
        
        if choice == '0':
            print("?? Goodbye!")
            break
        elif choice == '8':
            # Find and list images
            print("\n?? Searching for test images...")
            images = find_test_images()
            if images:
                print(f"Found {len(images)} images:")
                for i, img in enumerate(images, 1):
                    print(f"  {i:2d}. {os.path.basename(img)}")
            else:
                print("No images found")
            continue
        elif choice == '9':
            # Test document image extraction
            test_document_image_extraction()
            continue
        
        # Get image path for other tests
        image_path = get_test_image_path()
        if not image_path:
            continue
        
        # Run selected test
        if choice == '1':
            simple_ocr_test(image_path)
        elif choice == '2':
            advanced_ocr_test(image_path)
        elif choice == '3':
            test_rotation_detection(image_path)
        elif choice == '4':
            test_text_quality_analysis()
        elif choice == '5':
            test_enhanced_ocr_processor(image_path)
        elif choice == '6':
            test_opencv_processing(image_path)
        elif choice == '7':
            test_different_configs(image_path)
        else:
            print("? Invalid choice")


def get_test_image_path():
    """Get test image path from user"""
    images = find_test_images()
    
    if images:
        print(f"\nFound {len(images)} test images:")
        for i, img in enumerate(images, 1):
            print(f"  {i}. {os.path.basename(img)}")
        
        choice = input(f"Select image (1-{len(images)}) or enter custom path: ").strip()
        
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(images):
                return images[idx]
        else:
            # Check if it's a custom path
            if os.path.exists(choice):
                return choice
    
    # Manual input
    manual_path = input("Enter image path: ").strip()
    if manual_path and os.path.exists(manual_path):
        return manual_path
    
    print("? Invalid path or no image selected")
    return None


def test_document_image_extraction():
    """NEW: Test extraction of images from documents"""
    try:
        print(f"\n=== DOCUMENT IMAGE EXTRACTION TEST ===")
        
        # Try to import our advanced file utils
        try:
            from file_utils import AdvancedDocxParser
            parser = AdvancedDocxParser(extract_images=True, preserve_structure=True, extract_tables=True)
        except ImportError:
            print("? Advanced DOCX parser not available")
            return
        
        if not parser.is_available:
            print("? DOCX parsing dependencies missing")
            return
        
        # Find DOCX files to test
        docx_files = []
        try:
            for root, dirs, files in os.walk("./data/634/2025"):
                for file in files:
                    if file.lower().endswith('.docx'):
                        docx_files.append(os.path.join(root, file))
                        if len(docx_files) >= 5:  # Limit for testing
                            break
                if len(docx_files) >= 5:
                    break
        except:
            pass
        
        if not docx_files:
            print("? No DOCX files found for testing")
            return
        
        print(f"?? Found {len(docx_files)} DOCX files to test:")
        for i, docx_file in enumerate(docx_files, 1):
            print(f"  {i}. {os.path.basename(docx_file)}")
        
        choice = input(f"Select DOCX file (1-{len(docx_files)}): ").strip()
        
        if not choice.isdigit():
            print("? Invalid choice")
            return
        
        idx = int(choice) - 1
        if not (0 <= idx < len(docx_files)):
            print("? Invalid choice")
            return
        
        selected_file = docx_files[idx]
        
        print(f"\n?? Testing image extraction from: {os.path.basename(selected_file)}")
        
        # Extract images
        images = parser.extract_images_from_docx(selected_file)
        
        if images:
            print(f"? Found {len(images)} images in document")
            
            # Test OCR on first extracted image
            if len(images) > 0:
                image_data, image_name, image_format = images[0]
                
                print(f"?? Testing OCR on first image: {image_name}")
                
                # Save to temporary file and test OCR
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=image_format, delete=False) as temp_file:
                    temp_file.write(image_data)
                    temp_file_path = temp_file.name
                
                try:
                    # Test with enhanced OCR processor
                    test_enhanced_ocr_processor(temp_file_path)
                    
                    # Also test rotation detection on this image
                    print(f"\n?? Testing rotation detection on extracted image...")
                    test_rotation_detection(temp_file_path)
                    
                finally:
                    # Clean up temporary file
                    os.unlink(temp_file_path)
        else:
            print("? No images found in document")
            
    except Exception as e:
        print(f"? Document image extraction test error: {e}")


def comprehensive_test_suite(image_path):
    """Run comprehensive test suite on a single image"""
    print(f"\n" + "="*60)
    print("?? COMPREHENSIVE OCR TEST SUITE")
    print("="*60)
    print(f"Testing image: {os.path.basename(image_path)}")
    
    # Store all results
    test_results = {}
    
    # 1. Simple OCR
    print(f"\n1/7 Running simple OCR test...")
    simple_result = simple_ocr_test(image_path)
    test_results['simple'] = simple_result
    
    # 2. Advanced OCR
    print(f"\n2/7 Running advanced OCR test...")
    advanced_result = advanced_ocr_test(image_path)
    test_results['advanced'] = advanced_result
    
    # 3. Rotation detection
    print(f"\n3/7 Running rotation detection...")
    rotation_results, best_rotation = test_rotation_detection(image_path)
    test_results['rotation'] = (rotation_results, best_rotation)
    
    # 4. OpenCV processing
    print(f"\n4/7 Running OpenCV processing...")
    opencv_result = test_opencv_processing(image_path)
    test_results['opencv'] = opencv_result
    
    # 5. Configuration testing
    print(f"\n5/7 Running configuration tests...")
    config_results = test_different_configs(image_path)
    test_results['configs'] = config_results
    
    # 6. Enhanced OCR processor
    print(f"\n6/7 Running enhanced OCR processor...")
    enhanced_result = test_enhanced_ocr_processor(image_path)
    test_results['enhanced'] = enhanced_result
    
    # 7. Text quality analysis on best result
    print(f"\n7/7 Running text quality analysis...")
    if enhanced_result and enhanced_result.text:
        quality_results = test_text_quality_analysis([enhanced_result.text])
        test_results['quality_analysis'] = quality_results
    else:
        print("   ?? No text available for quality analysis")
        test_results['quality_analysis'] = []
    
    # Final comprehensive summary
    print(f"\n" + "="*60)
    print("?? COMPREHENSIVE TEST RESULTS SUMMARY")
    print("="*60)
    
    # Compare text lengths
    text_lengths = {}
    if simple_result:
        text_lengths['Simple OCR'] = len(simple_result)
    if advanced_result:
        text_lengths['Advanced OCR'] = len(advanced_result)
    if opencv_result:
        text_lengths['OpenCV'] = len(opencv_result)
    if enhanced_result:
        text_lengths['Enhanced OCR'] = len(enhanced_result.text)
    if best_rotation:
        text_lengths[f'Best Rotation ({best_rotation["angle"]}°)'] = best_rotation['text_length']
    
    if text_lengths:
        print("?? Text Length Comparison:")
        sorted_lengths = sorted(text_lengths.items(), key=lambda x: x[1], reverse=True)
        for method, length in sorted_lengths:
            print(f"   {method:<20}: {length:4d} characters")
    
    # Show rotation analysis
    if rotation_results:
        print(f"\n?? Rotation Analysis:")
        for result in rotation_results:
            status = "??" if best_rotation and result['angle'] == best_rotation['angle'] else "  "
            print(f"   {status} {result['angle']:3d}°: Quality {result['combined_quality']:.2f}, "
                  f"Length {result['text_length']:4d}")
    
    # Show configuration analysis  
    if config_results:
        good_configs = [r for r in config_results if r[2] > 0.3]  # Quality > 0.3
        print(f"\n?? Configuration Analysis:")
        print(f"   Tested configurations: {len(config_results)}")
        print(f"   Good quality results: {len(good_configs)}")
        if good_configs:
            best_config = max(good_configs, key=lambda x: x[2])
            print(f"   Best configuration: {best_config[0]} (quality: {best_config[2]:.2f})")
    
    # Enhanced OCR summary
    if enhanced_result:
        print(f"\n?? Enhanced OCR Results:")
        print(f"   Quality score: {enhanced_result.metadata.get('quality_score', 'N/A')}")
        if 'rotation_info' in enhanced_result.metadata:
            rotation_info = enhanced_result.metadata['rotation_info']
            best_angle = rotation_info.get('best_angle', 0)
            if best_angle != 0:
                print(f"   Applied rotation: {best_angle}°")
                improvement = rotation_info.get('quality_improvement', 0)
                print(f"   Quality improvement: +{improvement:.2f}")
            else:
                print(f"   No rotation applied (original was best)")
        
        # Show structure analysis if available
        if 'ocr_metrics' in enhanced_result.metadata:
            metrics = enhanced_result.metadata['ocr_metrics']
            if 'structure' in metrics:
                structure = metrics['structure']
                print(f"   Words found: {structure.get('words', 'N/A')}")
                print(f"   Letter ratio: {structure.get('letter_ratio', 0):.2f}")
                print(f"   Average word length: {structure.get('avg_word_length', 0):.1f}")
    
    # Final recommendations
    print(f"\n?? RECOMMENDATIONS:")
    
    # Best method overall
    best_length = 0
    best_method = "None"
    
    for method, length in text_lengths.items():
        if length > best_length:
            best_length = length
            best_method = method
    
    if best_method != "None":
        print(f"   ?? Most text extracted: {best_method} ({best_length} chars)")
    
    # Rotation recommendation
    if best_rotation and best_rotation['angle'] != 0:
        print(f"   ?? Rotation recommended: {best_rotation['angle']}° "
              f"(quality improvement: +{best_rotation.get('combined_quality', 0) - rotation_results[0]['combined_quality']:.2f})")
    else:
        print(f"   ?? No rotation needed")
    
    # Enhanced processor recommendation
    if enhanced_result:
        print(f"   ? Enhanced OCR processor provides best overall results")
        print(f"     - Automatic rotation detection")
        print(f"     - Text quality validation") 
        print(f"     - Comprehensive metadata")
    
    print("="*60)
    
    return test_results


def main():
    """Main function for enhanced OCR testing"""
    print("?? ENHANCED OCR DEBUG TEST SCRIPT - ENGLISH ONLY")
    print("="*60)
    print("Features:")
    print("  ?? Automatic rotation detection")
    print("  ?? Text quality analysis") 
    print("  ?? Enhanced OCR processing")
    print("  ?? Document image extraction")
    print("  ?? Comprehensive test suite")
    print("="*60)
    
    # Check Tesseract installation
    if not check_tesseract_installation():
        return
    
    # Check enhanced modules
    try:
        from ocr_processor import TextQualityAnalyzer, OCRProcessor
        print("? Enhanced OCR modules available")
        
        # Test text quality analyzer quickly
        analyzer = TextQualityAnalyzer('english')
        test_score, _ = analyzer.calculate_quality_score("This is a test sentence.")
        print(f"? Text quality analyzer working (test score: {test_score:.2f})")
        
    except ImportError as e:
        print(f"?? Enhanced modules not fully available: {e}")
        print("   Some advanced features may not work")
    
    # Run interactive menu
    try:
        interactive_test_menu()
    except KeyboardInterrupt:
        print(f"\n\n?? Testing interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n? Unexpected error: {e}")


def quick_test():
    """Quick test function for development"""
    print("? Quick OCR Test")
    
    # Find first available image
    images = find_test_images()
    if not images:
        print("? No test images found")
        return
    
    test_image = images[0]
    print(f"Testing: {os.path.basename(test_image)}")
    
    # Run comprehensive test
    results = comprehensive_test_suite(test_image)
    
    return results


if __name__ == "__main__":
    # Check if running in quick mode
    if len(sys.argv) > 1 and sys.argv[1] == '--quick':
        quick_test()
    else:
        main()