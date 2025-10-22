#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Remove all emoji from loading_helpers.py for Windows compatibility"""

import re

# Read the file
with open('rag_indexer/chunking_vectors/loading_helpers.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Define emoji replacements
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
}

# Apply replacements
for emoji, replacement in replacements.items():
    content = content.replace(emoji, replacement)

# Write back
with open('rag_indexer/chunking_vectors/loading_helpers.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully removed all emoji from loading_helpers.py")
print(f"Replaced {len(replacements)} emoji types")
