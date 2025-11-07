# utils/encoding_fix.py
# Utility to detect and fix encoding issues in Python files

import os
import chardet
import codecs
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def detect_file_encoding(file_path):
    """Detect file encoding using chardet"""
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)
            return result['encoding'], result['confidence']
    except Exception as e:
        logger.error(f"Error detecting encoding for {file_path}: {e}")
        return None, 0

def fix_file_encoding(file_path, target_encoding='utf-8'):
    """Fix file encoding by converting to UTF-8"""
    try:
        # Detect current encoding
        current_encoding, confidence = detect_file_encoding(file_path)
        
        if not current_encoding:
            print(f"? Could not detect encoding for {file_path}")
            return False
        
        if current_encoding.lower() == target_encoding.lower():
            print(f"? {file_path} is already in {target_encoding}")
            return True
        
        print(f"?? Converting {file_path}: {current_encoding} (confidence: {confidence:.2f}) -> {target_encoding}")
        
        # Create backup
        backup_path = f"{file_path}.backup"
        os.rename(file_path, backup_path)
        
        # Read with detected encoding
        with codecs.open(backup_path, 'r', encoding=current_encoding, errors='ignore') as f:
            content = f.read()
        
        # Write with UTF-8 encoding
        with codecs.open(file_path, 'w', encoding=target_encoding) as f:
            f.write(content)
        
        print(f"? Successfully converted {file_path}")
        
        # Remove backup if successful
        os.remove(backup_path)
        
        return True
        
    except Exception as e:
        print(f"? Error fixing {file_path}: {e}")
        # Restore backup if exists
        backup_path = f"{file_path}.backup"
        if os.path.exists(backup_path):
            os.rename(backup_path, file_path)
        return False

def fix_project_encoding(project_dir=".", file_extensions=[".py"]):
    """Fix encoding for all specified files in project"""
    print("?? Fixing encoding issues in project files...")
    
    project_path = Path(project_dir)
    files_to_fix = []
    
    # Collect all files with specified extensions
    for ext in file_extensions:
        files_to_fix.extend(project_path.rglob(f"*{ext}"))
    
    print(f"?? Found {len(files_to_fix)} files to check")
    
    fixed_count = 0
    error_count = 0
    
    for file_path in files_to_fix:
        try:
            if fix_file_encoding(str(file_path)):
                fixed_count += 1
            else:
                error_count += 1
        except Exception as e:
            print(f"? Failed to process {file_path}: {e}")
            error_count += 1
    
    print(f"\n?? Results:")
    print(f"  ? Fixed: {fixed_count} files")
    print(f"  ? Errors: {error_count} files")
    print(f"  ?? Total: {len(files_to_fix)} files processed")

def scan_project_encodings(project_dir=".", file_extensions=[".py"]):
    """Scan project files and report encoding issues"""
    print("?? Scanning project for encoding issues...")
    
    project_path = Path(project_dir)
    files_to_scan = []
    
    # Collect all files with specified extensions
    for ext in file_extensions:
        files_to_scan.extend(project_path.rglob(f"*{ext}"))
    
    print(f"?? Scanning {len(files_to_scan)} files")
    
    encoding_stats = {}
    problematic_files = []
    
    for file_path in files_to_scan:
        try:
            encoding, confidence = detect_file_encoding(str(file_path))
            
            if encoding:
                if encoding not in encoding_stats:
                    encoding_stats[encoding] = []
                encoding_stats[encoding].append(str(file_path))
                
                # Flag files with non-UTF-8 encoding or low confidence
                if encoding.lower() != 'utf-8' or confidence < 0.9:
                    problematic_files.append({
                        'file': str(file_path),
                        'encoding': encoding,
                        'confidence': confidence
                    })
            else:
                problematic_files.append({
                    'file': str(file_path),
                    'encoding': 'UNKNOWN',
                    'confidence': 0
                })
                
        except Exception as e:
            print(f"? Error scanning {file_path}: {e}")
    
    # Report results
    print(f"\n?? Encoding Statistics:")
    for encoding, files in encoding_stats.items():
        print(f"  {encoding}: {len(files)} files")
    
    if problematic_files:
        print(f"\n?? Problematic Files ({len(problematic_files)}):")
        for item in problematic_files:
            print(f"  ?? {item['file']}")
            print(f"     Encoding: {item['encoding']} (confidence: {item['confidence']:.2f})")
    else:
        print(f"\n? All files appear to have good UTF-8 encoding!")
    
    return problematic_files

def interactive_fix():
    """Interactive encoding fix utility"""
    print("??? Interactive Encoding Fix Utility")
    print("=" * 50)
    
    while True:
        print("\nOptions:")
        print("1. Scan project for encoding issues")
        print("2. Fix all encoding issues")
        print("3. Fix specific file")
        print("4. Exit")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == "1":
            print("\n?? Scanning project...")
            problematic = scan_project_encodings()
            if problematic:
                print(f"\nFound {len(problematic)} files with potential encoding issues.")
                fix_choice = input("Do you want to fix them? (y/n): ").strip().lower()
                if fix_choice == 'y':
                    fix_project_encoding()
        
        elif choice == "2":
            print("\n?? Fixing all encoding issues...")
            fix_project_encoding()
        
        elif choice == "3":
            file_path = input("Enter file path: ").strip()
            if os.path.exists(file_path):
                fix_file_encoding(file_path)
            else:
                print(f"? File not found: {file_path}")
        
        elif choice == "4":
            print("?? Goodbye!")
            break
        
        else:
            print("? Invalid option")

def quick_fix_main_files():
    """Quick fix for main project files"""
    print("?? Quick Fix for Main Project Files")
    
    main_files = [
        "main_app.py"
    ]
    
    for file_path in main_files:
        if os.path.exists(file_path):
            print(f"\n?? Checking {file_path}...")
            fix_file_encoding(file_path)
        else:
            print(f"?? File not found: {file_path}")

if __name__ == "__main__":
    print("?? Encoding Fix Utility")
    print("Choose fix method:")
    print("1. Interactive mode")
    print("2. Quick fix main files")
    print("3. Full project scan and fix")
    
    choice = input("Select (1-3): ").strip()
    
    if choice == "1":
        interactive_fix()
    elif choice == "2":
        quick_fix_main_files()
    elif choice == "3":
        scan_project_encodings()
        fix_input = input("\nFix all issues? (y/n): ").strip().lower()
        if fix_input == 'y':
            fix_project_encoding()
    else:
        print("? Invalid choice")