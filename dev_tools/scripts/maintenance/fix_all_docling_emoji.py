#!/usr/bin/env python3
"""Remove all emoji from docling_processor directory"""

from pathlib import Path

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
    '📁': '[*]',
    '📂': '[*]',
    '📑': '[*]',
}

docling_dir = Path('rag_indexer/docling_processor')
fixed_count = 0

for py_file in docling_dir.glob('*.py'):
    with open(py_file, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    for emoji, replacement in replacements.items():
        content = content.replace(emoji, replacement)

    if content != original:
        with open(py_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed: {py_file.name}")
        fixed_count += 1
    else:
        print(f"No changes: {py_file.name}")

print(f"\nTotal files fixed: {fixed_count}")
