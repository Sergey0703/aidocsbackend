#!/usr/bin/env python3
"""Investigate picture content in Vehicle Registration Certificate"""

from pathlib import Path
from docling_core.types import DoclingDocument

# Load JSON
json_path = Path("rag_indexer/data/json/Vehicle Registration Certificate.json")
doc = DoclingDocument.load_from_json(str(json_path))

print("Document structure:")
print(f"  Total texts: {len(doc.texts)}")
print(f"  Total pictures: {len(doc.pictures)}")
print(f"  Body children: {len(doc.body.children)}")

# Analyze body children
print("\nBody children:")
for i, child_ref in enumerate(doc.body.children):
    print(f"  {i}: {child_ref}")

# Check the picture
if doc.pictures:
    picture = doc.pictures[0]
    print(f"\nPicture 0:")
    print(f"  Label: {picture.label}")
    print(f"  Parent: {picture.parent}")
    print(f"  Children: {len(picture.children)}")
    print(f"  First 5 children:")
    for i, child_ref in enumerate(picture.children[:5]):
        print(f"    {i}: {child_ref}")

# Count texts by parent
texts_in_body = 0
texts_in_picture = 0
texts_in_groups = 0

for text in doc.texts:
    if text.parent:
        parent_ref = text.parent.cref if hasattr(text.parent, 'cref') else str(text.parent)
        if '#/body' in parent_ref:
            texts_in_body += 1
        elif '#/pictures' in parent_ref:
            texts_in_picture += 1
        elif '#/groups' in parent_ref:
            texts_in_groups += 1

print(f"\nText distribution:")
print(f"  Texts in body: {texts_in_body}")
print(f"  Texts in picture: {texts_in_picture}")
print(f"  Texts in groups: {texts_in_groups}")

# Try to extract text from picture
print(f"\nTrying to get text content...")
if doc.pictures:
    picture = doc.pictures[0]
    print(f"Picture has {len(picture.children)} children")

    # Can we export to text?
    try:
        text_content = doc.export_to_text()
        print(f"\nExported text length: {len(text_content)}")
        print(f"First 500 chars:\n{text_content[:500]}")
    except Exception as e:
        print(f"Export failed: {e}")
