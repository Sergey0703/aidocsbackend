#!/usr/bin/env python3
"""
Debug script to find the problematic file causing crashes at batch 3
"""

import os
import logging
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

# --- IMPORTS ---
from llama_index.core import SimpleDirectoryReader, Document
from llama_index.core.node_parser import SentenceSplitter

def find_problematic_file():
    """Find the exact file causing the crash at chunks 201-300"""
    
    load_dotenv()
    
    DOCUMENTS_DIR = os.getenv("DOCUMENTS_DIR", "./data/634/2025")
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1024"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "256"))
    MIN_CHUNK_LENGTH = int(os.getenv("MIN_CHUNK_LENGTH", "100"))
    ENABLE_OCR = os.getenv("ENABLE_OCR", "true").lower() == "true"
    
    print("=== FINDING PROBLEMATIC FILE ===")
    print(f"Documents directory: {DOCUMENTS_DIR}")
    print(f"Target chunks: 201-300 (batch 3)")
    print("=" * 50)
    
    # Initialize components
    node_parser = SentenceSplitter(
        chunk_size=CHUNK_SIZE, 
        chunk_overlap=CHUNK_OVERLAP,
        paragraph_separator="\n\n",
        secondary_chunking_regex="[.!?]\\s+"
    )
    
    try:
        # 1. Load documents exactly like in main script
        print("Loading documents...")
        reader = SimpleDirectoryReader(DOCUMENTS_DIR, recursive=True)
        text_documents = reader.load_data(num_workers=4)
        
        # Skip OCR for debugging speed
        documents = text_documents
        print(f"Loaded {len(documents)} documents")
        
        # 2. Filter documents exactly like in main script
        documents_with_content = []
        for doc in documents:
            text_content = doc.text.strip()
            if text_content and len(text_content) >= MIN_CHUNK_LENGTH:
                documents_with_content.append(doc)
        
        print(f"Filtered to {len(documents_with_content)} valid documents")
        
        # 3. Create chunks and track file mapping
        print("Creating chunks and tracking file mapping...")
        all_nodes = node_parser.get_nodes_from_documents(documents_with_content, show_progress=True)
        
        # Filter nodes exactly like in main script
        valid_nodes = []
        chunk_to_file_mapping = {}
        
        for idx, node in enumerate(all_nodes):
            content = node.get_content().strip()
            if (content and 
                len(content) >= MIN_CHUNK_LENGTH and 
                len(content.split()) > 5 and
                not content.isdigit()):
                
                # Add metadata like in main script
                if 'file_name' not in node.metadata:
                    node.metadata['file_name'] = node.get_metadata_str()
                node.metadata['text'] = content
                node.metadata['indexed_at'] = datetime.now().isoformat()
                
                chunk_index = len(valid_nodes)
                valid_nodes.append(node)
                
                # Track which file this chunk came from
                file_path = node.metadata.get('file_path', 'Unknown')
                file_name = node.metadata.get('file_name', 'Unknown')
                chunk_to_file_mapping[chunk_index] = {
                    'file_path': file_path,
                    'file_name': file_name,
                    'chunk_length': len(content),
                    'chunk_preview': content[:100] + "..." if len(content) > 100 else content
                }
        
        print(f"Created {len(valid_nodes)} valid chunks")
        
        # 4. Analyze problematic range (chunks 201-300)
        print("\n" + "=" * 50)
        print("ANALYZING PROBLEMATIC RANGE (chunks 201-300)")
        print("=" * 50)
        
        problematic_files = {}
        
        for chunk_idx in range(200, min(300, len(valid_nodes))):  # 0-based indexing
            if chunk_idx in chunk_to_file_mapping:
                file_info = chunk_to_file_mapping[chunk_idx]
                file_path = file_info['file_path']
                
                if file_path not in problematic_files:
                    problematic_files[file_path] = {
                        'file_name': file_info['file_name'],
                        'chunks': [],
                        'total_chunks': 0,
                        'chunk_lengths': []
                    }
                
                problematic_files[file_path]['chunks'].append(chunk_idx + 1)  # 1-based for display
                problematic_files[file_path]['total_chunks'] += 1
                problematic_files[file_path]['chunk_lengths'].append(file_info['chunk_length'])
        
        # 5. Display results
        print(f"Files in problematic range (chunks 201-300):")
        print("-" * 50)
        
        for file_path, info in problematic_files.items():
            avg_chunk_length = sum(info['chunk_lengths']) / len(info['chunk_lengths'])
            chunks_str = f"{info['chunks'][0]}-{info['chunks'][-1]}" if len(info['chunks']) > 1 else str(info['chunks'][0])
            
            print(f"FILE: {info['file_name']}")
            print(f"  Path: {file_path}")
            print(f"  Chunks: {chunks_str} ({info['total_chunks']} total)")
            print(f"  Avg chunk length: {avg_chunk_length:.0f} chars")
            print(f"  Chunk lengths: {info['chunk_lengths']}")
            print()
        
        # 6. Check for suspicious patterns
        print("=" * 50)
        print("SUSPICIOUS PATTERN ANALYSIS")
        print("=" * 50)
        
        suspicious_files = []
        
        for file_path, info in problematic_files.items():
            suspicion_reasons = []
            
            # Check for very long chunks
            if max(info['chunk_lengths']) > 5000:
                suspicion_reasons.append(f"Very long chunks (max: {max(info['chunk_lengths'])})")
            
            # Check for very short chunks
            if min(info['chunk_lengths']) < 50:
                suspicion_reasons.append(f"Very short chunks (min: {min(info['chunk_lengths'])})")
            
            # Check for unusual file extensions
            if file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                suspicion_reasons.append("Image file (OCR content)")
            
            # Check for many chunks from one file
            if info['total_chunks'] > 20:
                suspicion_reasons.append(f"Many chunks from one file ({info['total_chunks']})")
            
            if suspicion_reasons:
                suspicious_files.append({
                    'file_path': file_path,
                    'file_name': info['file_name'],
                    'reasons': suspicion_reasons,
                    'chunks': info['chunks']
                })
        
        if suspicious_files:
            print("SUSPICIOUS FILES FOUND:")
            for i, file_info in enumerate(suspicious_files, 1):
                print(f"\n{i}. {file_info['file_name']}")
                print(f"   Path: {file_info['file_path']}")
                print(f"   Chunks: {file_info['chunks']}")
                print(f"   Suspicion reasons:")
                for reason in file_info['reasons']:
                    print(f"     - {reason}")
        else:
            print("No obviously suspicious files found.")
        
        # 7. Detailed chunk analysis for exact crash point
        print("\n" + "=" * 50)
        print("DETAILED ANALYSIS OF CRASH POINT (chunk 201)")
        print("=" * 50)
        
        if 200 < len(valid_nodes):  # Check chunk 201 (0-based index 200)
            crash_chunk = valid_nodes[200]
            crash_info = chunk_to_file_mapping[200]
            
            print(f"CRASH CHUNK #201:")
            print(f"  File: {crash_info['file_name']}")
            print(f"  Path: {crash_info['file_path']}")
            print(f"  Length: {crash_info['chunk_length']} characters")
            print(f"  Content preview:")
            print(f"    {crash_info['chunk_preview']}")
            print()
            
            # Check chunk content for issues
            content = crash_chunk.get_content()
            metadata = crash_chunk.metadata
            
            print(f"  Metadata keys: {list(metadata.keys())}")
            print(f"  Has special characters: {any(ord(c) > 127 for c in content[:500])}")
            print(f"  Content type: {type(content)}")
            print(f"  Encoding issues: {repr(content[:100])}")
        
        print("\n" + "=" * 50)
        print("RECOMMENDATIONS:")
        print("=" * 50)
        
        if suspicious_files:
            print("1. Try temporarily moving these suspicious files:")
            for file_info in suspicious_files[:3]:  # Top 3 most suspicious
                print(f"   mv '{file_info['file_path']}' /tmp/")
        
        print("2. Or add skip logic for chunks 201-300:")
        print("   if 200 <= i < 300: continue")
        
        print("3. Or process files individually to isolate the problem")
        
    except Exception as e:
        print(f"ERROR during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    find_problematic_file()
