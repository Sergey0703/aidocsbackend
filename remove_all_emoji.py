#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Remove ALL emoji from all Python files for Windows compatibility"""

import os
from pathlib import Path

# Define comprehensive emoji replacements
replacements = {
    '→': '->',
    '✅': '[+]',
    '❌': '[-]',
    '⚠️': '[!]',
    '🚀': '[*]',
    '📄': '[*]',
    '🧩': '[*]',
    '🔗': '[*]',
    '🔧': '[*]',
    '📊': '[*]',
    '🎉': '[*]',
    '✓': '[+]',
    '📝': '[*]',
    '⏱️': '[*]',
    '🔍': '[*]',
    '💡': '[*]',
    '💾': '[*]',
    '📂': '[*]',
    '🚫': '[*]',
    '📁': '[*]',
    '📋': '[*]',
    '❓': '[?]',
    '🏷️': '[*]',
    '🗑️': '[*]',
    '🔄': '[*]',
    '📈': '[*]',
    '📉': '[*]',
    '📌': '[*]',
    '✗': '[-]',
    '⚡': '[*]',
    '🎯': '[*]',
    '🔎': '[*]',
    '⏰': '[*]',
}

# Files to process
files_to_process = [
    'rag_indexer/chunking_vectors/analysis_helpers.py',
    'rag_indexer/chunking_vectors/batch_processor.py',
    'rag_indexer/chunking_vectors/chunk_helpers.py',
    'rag_indexer/chunking_vectors/chunk_helpers_hybrid.py',
    'rag_indexer/chunking_vectors/config.py',
    'rag_indexer/chunking_vectors/file_utils_core.py',
    'rag_indexer/chunking_vectors/hybrid_chunker.py',
    'rag_indexer/chunking_vectors/incremental_indexer.py',
    'rag_indexer/chunking_vectors/loading_helpers.py',
    'rag_indexer/chunking_vectors/RegistryManager.py',
    'rag_indexer/chunking_vectors/registry_manager.py',
    'rag_indexer/chunking_vectors/__init__.py',
]

total_fixed = 0
for file_path in files_to_process:
    if not Path(file_path).exists():
        print(f"Skipping {file_path} (not found)")
        continue

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Apply replacements
        for emoji, replacement in replacements.items():
            content = content.replace(emoji, replacement)

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed: {file_path}")
            total_fixed += 1
        else:
            print(f"No changes: {file_path}")
    except Exception as e:
        print(f"ERROR processing {file_path}: {e}")

print(f"\nTotal files fixed: {total_fixed}/{len(files_to_process)}")
print(f"Emoji types replaced: {len(replacements)}")
