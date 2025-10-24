#!/usr/bin/env python3
"""Analyze Docling JSON structure for chunking investigation"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv('rag_indexer/.env')

json_dir = os.getenv('JSON_OUTPUT_DIR', 'rag_indexer/data/json')
cvrt_json = Path(json_dir) / '1761320270_CVRT_Pass_Statement.json'

print("\n" + "="*80)
print("ANALYZING DOCLING JSON STRUCTURE")
print("="*80 + "\n")

if not cvrt_json.exists():
    print(f"ERROR: JSON file not found: {cvrt_json}")
    exit(1)

print(f"File: {cvrt_json}")
print(f"Size: {cvrt_json.stat().st_size} bytes\n")

with open(cvrt_json, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Top-level keys: {list(data.keys())}\n")

# Check if it's a DoclingDocument structure
if 'name' in data:
    print(f"Document name: {data['name']}")

if 'body' in data:
    body = data['body']
    print(f"\nBODY structure:")
    print(f"  Type: {type(body)}")
    if isinstance(body, dict):
        print(f"  Keys: {list(body.keys())}")

# Look for common DoclingDocument fields
fields_to_check = ['texts', 'tables', 'pictures', 'main_text', 'pages', 'groups', 'items']
for field in fields_to_check:
    if field in data:
        value = data[field]
        if isinstance(value, list):
            print(f"\n{field.upper()}: {len(value)} elements")
            if len(value) > 0:
                print(f"  First element type: {type(value[0])}")
                if isinstance(value[0], dict):
                    print(f"  First element keys: {list(value[0].keys())}")
        elif isinstance(value, dict):
            print(f"\n{field.upper()}: dict with {len(value)} keys")
            print(f"  Keys: {list(value.keys())}")
        else:
            print(f"\n{field.upper()}: {type(value)}")

# Check for document structure (DoclingDocument API)
if 'main_text' in data:
    main_text = data['main_text']
    print(f"\nMAIN_TEXT analysis:")
    print(f"  Type: {type(main_text)}")
    print(f"  Content preview: {str(main_text)[:200]}...")

# Sample the first few items if there's an 'items' field (common in DoclingDocument)
if 'items' in data and isinstance(data['items'], list):
    print(f"\nFIRST 5 ITEMS:")
    for i, item in enumerate(data['items'][:5], 1):
        if isinstance(item, dict):
            label = item.get('label', 'NO_LABEL')
            text = item.get('text', '')
            print(f"  [{i}] Label: {label}, Text length: {len(text)}")
            print(f"      Preview: {text[:80]}...")

print("\n" + "="*80)
