#!/usr/bin/env python3
"""
Complete Storage Cleanup Script
Deletes ALL files from Supabase Storage bucket recursively
"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv


def list_all_files_recursive(supabase, bucket, path="", prefix=""):
    """Recursively list all files in storage"""
    all_files = []
    try:
        items = supabase.storage.from_(bucket).list(path)

        for item in items:
            item_name = item.get('name')
            if not item_name:
                continue

            if path:
                full_path = f"{path}/{item_name}"
            else:
                full_path = item_name

            print(f"{prefix}Found: {full_path}")
            all_files.append(full_path)

            # Try to list subdirectories
            try:
                subitems = supabase.storage.from_(bucket).list(full_path)
                if subitems:
                    # It's a folder with contents
                    subfiles = list_all_files_recursive(supabase, bucket, full_path, prefix + "  ")
                    all_files.extend(subfiles)
            except:
                pass  # It's a file, not a folder

    except Exception as e:
        print(f"{prefix}Error listing {path}: {e}")

    return all_files


def main():
    load_dotenv()

    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    bucket = os.getenv('SUPABASE_STORAGE_BUCKET', 'vehicle-documents')

    if not url or not key:
        print("[!] Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env")
        return

    print("="*70)
    print("COMPLETE STORAGE CLEANUP")
    print("="*70)
    print(f"Bucket: {bucket}")
    print(f"URL: {url}")
    print("="*70)

    supabase: Client = create_client(url, key)

    print("\n[*] Scanning all files recursively...")
    all_files = list_all_files_recursive(supabase, bucket)

    print(f"\n[*] Total items found: {len(all_files)}")

    if not all_files:
        print("[+] Storage is already empty!")
        return

    # Sort by depth (deepest first) to delete files before folders
    all_files.sort(key=lambda x: x.count('/'), reverse=True)

    print("\n[*] Deleting all files (deepest first)...")
    deleted = 0
    failed = 0

    for file_path in all_files:
        try:
            supabase.storage.from_(bucket).remove([file_path])
            print(f"   [+] Deleted: {file_path}")
            deleted += 1
        except Exception as e:
            print(f"   [!] Failed to delete {file_path}: {e}")
            failed += 1

    print("\n" + "="*70)
    print(f"[*] Deleted: {deleted}")
    print(f"[*] Failed: {failed}")
    print("="*70)

    # Final verification
    print("\n[*] Final verification...")
    remaining = supabase.storage.from_(bucket).list()

    if remaining:
        print(f"[!] WARNING: {len(remaining)} items still in root:")
        for item in remaining:
            print(f"    - {item.get('name')}")
    else:
        print("[+] SUCCESS: Storage bucket is completely empty!")


if __name__ == "__main__":
    main()
