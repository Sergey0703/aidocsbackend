#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# rag_indexer/chunking_vectors/markdown_loader.py
# Complete markdown loader with registry_id enrichment

import os
import json
import logging
import time
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional
from llama_index.core import Document

logger = logging.getLogger(__name__)


def clean_content_from_null_bytes(content: str) -> str:
    """Clean content from null bytes and other problematic characters."""
    if not isinstance(content, str):
        return content
    content = content.replace('\u0000', '').replace('\x00', '')
    cleaned_content = ''.join(char for char in content if ord(char) >= 32 or char in '\n\t\r')
    return cleaned_content


def clean_metadata_recursive(obj: Any) -> Any:
    """Recursively clean metadata from null bytes."""
    if isinstance(obj, dict):
        return {k: clean_metadata_recursive(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_metadata_recursive(v) for v in obj]
    elif isinstance(obj, str):
        cleaned = obj.replace('\u0000', '').replace('\x00', '')
        return cleaned[:2048]  # Limit metadata string length for safety
    else:
        return obj


class MarkdownLoader:
    """
    Simple markdown file loader for preprocessed documents from Docling.
    Enriches document metadata with registry_id for database integration.
      Supports both local filesystem and Supabase Storage modes.
    """

    def __init__(self, input_dir: str, recursive: bool = True, config: Any = None, storage_manager=None):
        """
        Initialize markdown loader.

        Args:
            input_dir: Input directory path (markdown files from Docling).
            recursive: Whether to scan recursively.
            config: Configuration object.
            storage_manager: Optional SupabaseStorageManager for Storage mode.
        """
        self.input_dir = Path(input_dir)
        self.metadata_dir = self.input_dir / "_metadata"
        self.recursive = recursive
        self.config = config
        self.storage_manager = storage_manager
        self.blacklist_directories = getattr(config, 'BLACKLIST_DIRECTORIES', [])
        
        self.loading_stats = {
            'total_files_scanned': 0,
            'markdown_files_found': 0,
            'documents_created': 0,
            'failed_files': 0,
            'failed_files_list': [],
            'total_characters': 0,
            'metadata_files_loaded': 0,
            'metadata_files_missing': 0,
            'registry_enrichments': 0,
            'registry_failures': 0,
            'loading_time': 0.0,
        }

    def _is_blacklisted(self, path: Path) -> bool:
        """Check if a path is in a blacklisted directory."""
        path_parts = {part.lower() for part in path.parts}
        blacklisted_parts = {part.lower() for part in self.blacklist_directories}
        return not path_parts.isdisjoint(blacklisted_parts)

    def _scan_markdown_files(self) -> List[str]:
        """Scan directory for markdown files, respecting blacklists."""
        markdown_files = []
        
        if not self.input_dir.exists():
            logger.error(f"Input directory does not exist: {self.input_dir}")
            return []

        glob_pattern = "**/*.md" if self.recursive else "*.md"
        
        for file_path in self.input_dir.glob(glob_pattern):
            self.loading_stats['total_files_scanned'] += 1
            if file_path.is_file() and not self._is_blacklisted(file_path):
                markdown_files.append(str(file_path))
        
        self.loading_stats['markdown_files_found'] = len(markdown_files)
        return markdown_files

    def _read_markdown_file(self, file_path: str) -> Tuple[Optional[str], Optional[str]]:
        """Read a single markdown file with encoding fallbacks."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            cleaned_content = clean_content_from_null_bytes(content)
            
            if not cleaned_content.strip():
                return None, "empty_file"
            
            return cleaned_content, None
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    logger.warning(f"UTF-8 decoding error in {file_path}, reading with replacements.")
                    content = f.read()
                return clean_content_from_null_bytes(content), None
            except Exception as e:
                return None, f"read_error_fallback: {e}"
        except Exception as e:
            return None, f"read_error: {e}"

    def _load_accompanying_metadata(self, md_file_path: Path) -> Dict[str, Any]:
        """Loads metadata from the corresponding .json file in the _metadata directory."""
        try:
            json_filename = f"{md_file_path.stem}.json"
            metadata_path = self.metadata_dir / json_filename
            
            if metadata_path.exists():
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                self.loading_stats['metadata_files_loaded'] += 1
                return metadata
            else:
                logger.warning(f"Metadata file not found for {md_file_path.name} at {metadata_path}")
                self.loading_stats['metadata_files_missing'] += 1
                return {}
        except Exception as e:
            logger.error(f"Failed to load or parse metadata for {md_file_path.name}: {e}")
            self.loading_stats['metadata_files_missing'] += 1
            return {}

    def _create_document_from_markdown(self, file_path: str, content: str) -> Optional[Document]:
        """
        Creates a LlamaIndex Document, enriched with metadata from its .json file.
        """
        try:
            md_file_path = Path(file_path)
            
            json_metadata = self._load_accompanying_metadata(md_file_path)
            
            base_metadata = {
                'file_path': str(md_file_path.resolve()),
                'file_name': md_file_path.name,
                'file_type': 'markdown',
                'file_size': md_file_path.stat().st_size,
                'content_length': len(content),
                'word_count': len(content.split()),
                'loader_timestamp': datetime.now().isoformat(),
            }

            # Look for corresponding JSON file (for Hybrid Chunking)
            # JSON files should be in data/json/ with same structure as data/markdown/
            json_dir = self.input_dir.parent / "json"
            if json_dir.exists():
                try:
                    # Calculate relative path from markdown dir
                    rel_path = md_file_path.relative_to(self.input_dir)
                    # Build corresponding JSON path (same structure, .json extension)
                    json_path = json_dir / rel_path.parent / f"{md_file_path.stem}.json"
                    if json_path.exists():
                        base_metadata['json_path'] = str(json_path.resolve())
                        logger.info(f"[+] Found JSON for {md_file_path.name}: {json_path.name}")
                    else:
                        logger.warning(f"  No JSON file for {md_file_path.name} (expected: {json_path.name})")
                        logger.warning(f"    Will use markdown fallback (structure may be lost)")
                except Exception as e:
                    logger.warning(f"  Could not locate JSON file for {md_file_path.name}: {e}")
            else:
                logger.warning(f"  JSON directory not found: {json_dir}")

            final_metadata = {**base_metadata, **json_metadata}
            cleaned_metadata = clean_metadata_recursive(final_metadata)

            document = Document(
                id_=str(uuid.uuid4()),
                text=content,
                metadata=cleaned_metadata
            )
            return document
        except Exception as e:
            logger.error(f"Failed to create LlamaIndex Document from {file_path}: {e}", exc_info=True)
            return None

    def _enrich_with_registry_id(self, document: Document, registry_manager) -> Document:
        """
        Enrich document metadata with registry_id, original_path, and original_file_hash
        from document_registry table (for incremental indexing support).

        Args:
            document: LlamaIndex Document
            registry_manager: RegistryManager instance

        Returns:
            Document: Enriched document with registry_id, original_path, original_file_hash
        """
        try:
            file_path = document.metadata.get('file_path')
            if not file_path:
                logger.warning(f"Document missing file_path, cannot create registry entry")
                self.loading_stats['registry_failures'] += 1
                return document

            # Get full registry information (registry_id, storage_path, file_hash)
            registry_info = registry_manager.get_registry_info_by_markdown_path(file_path)

            if registry_info:
                # Add registry_id to metadata
                document.metadata['registry_id'] = registry_info['registry_id']

                # Add original_path for incremental indexing (use storage_path or raw_file_path)
                original_path = registry_info.get('storage_path') or registry_info.get('raw_file_path')
                if original_path:
                    document.metadata['original_path'] = original_path

                # Add file_hash for change detection
                if registry_info.get('file_hash'):
                    document.metadata['original_file_hash'] = registry_info['file_hash']

                self.loading_stats['registry_enrichments'] += 1
                logger.debug(f"[+] Added registry info to {document.metadata.get('file_name')}: "
                           f"registry_id={registry_info['registry_id']}, "
                           f"original_path={original_path}, "
                           f"file_hash={'present' if registry_info.get('file_hash') else 'missing'}")
            else:
                # Fallback: create registry entry with only markdown path
                registry_id = registry_manager.get_or_create_registry_entry(file_path=file_path)
                if registry_id:
                    document.metadata['registry_id'] = registry_id
                    logger.warning(f"[!] Created registry entry without original_path/file_hash for {file_path}")
                else:
                    logger.error(f"[-] Failed to get registry_id for {file_path}")
                    self.loading_stats['registry_failures'] += 1

            return document

        except Exception as e:
            logger.error(f"Failed to enrich document with registry_id: {e}", exc_info=True)
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            self.loading_stats['registry_failures'] += 1
            return document

    def _load_from_storage(self, registry_manager) -> List[Document]:
        """
          Load documents from Supabase Storage via document_registry.
        Downloads MD/JSON files to temporary directory, loads them, then cleans up.
        """
        import tempfile
        import os

        if not self.storage_manager:
            raise ValueError("Storage manager not provided! Cannot load from Storage.")

        logger.info("[*]   STORAGE MODE: Loading documents from Supabase Storage")

        # Create temporary directory for downloads
        temp_dir = Path(tempfile.mkdtemp(prefix="markdown_loader_"))
        logger.info(f"[*] Temporary directory: {temp_dir}")

        try:
            # Query registry for documents with Storage paths
            import psycopg2
            conn = psycopg2.connect(registry_manager.connection_string)
            cur = conn.cursor()

            cur.execute("""
                SELECT
                    id,
                    markdown_storage_path,
                    markdown_metadata_path,
                    json_storage_path,
                    original_filename,
                    storage_path,
                    file_hash
                FROM vecs.document_registry
                WHERE markdown_storage_path IS NOT NULL
                  AND status = 'pending_indexing'
                ORDER BY uploaded_at DESC
            """)

            registry_records = cur.fetchall()
            logger.info(f"[*] Found {len(registry_records)} documents in Storage")

            documents = []

            for record in registry_records:
                registry_id = record[0]
                md_storage_path = record[1]
                metadata_storage_path = record[2]
                json_storage_path = record[3]
                original_filename = record[4]
                storage_path = record[5]  # For incremental indexing
                file_hash = record[6]  # For change detection

                try:
                    # Download MD file
                    logger.info(f"     Downloading {original_filename} MD from Storage...")
                    md_temp_path = Path(self.storage_manager.download_to_temp(md_storage_path))

                    # Download metadata JSON (optional)
                    metadata_temp_path = None
                    if metadata_storage_path:
                        logger.info(f"     Downloading metadata JSON...")
                        metadata_temp_path = Path(self.storage_manager.download_to_temp(metadata_storage_path))

                    # Download DoclingDocument JSON (for HybridChunker)
                    json_temp_path = None
                    if json_storage_path:
                        logger.info(f"     Downloading DoclingDocument JSON...")
                        json_temp_path = Path(self.storage_manager.download_to_temp(json_storage_path))

                    # Read MD content
                    content, error = self._read_markdown_file(str(md_temp_path))

                    if error or not content:
                        logger.error(f"   [ERR] Failed to read {original_filename}: {error}")
                        self.loading_stats['failed_files'] += 1
                        continue

                    # Load metadata JSON if available
                    json_metadata = {}
                    if metadata_temp_path and metadata_temp_path.exists():
                        try:
                            with open(metadata_temp_path, 'r', encoding='utf-8') as f:
                                json_metadata = json.load(f)
                            self.loading_stats['metadata_files_loaded'] += 1
                        except Exception as meta_err:
                            logger.warning(f"     Failed to load metadata: {meta_err}")

                    # Build document metadata
                    doc_metadata = {
                        'file_path': str(md_temp_path),  # Temporary path
                        'file_name': Path(md_storage_path).name,
                        'file_type': 'markdown',
                        'content_length': len(content),
                        'loader_timestamp': datetime.now().isoformat(),
                        'registry_id': registry_id,  # Add registry_id immediately
                        **json_metadata
                    }

                    # Add incremental indexing metadata (for change detection)
                    if storage_path:
                        doc_metadata['original_path'] = storage_path
                    if file_hash:
                        doc_metadata['original_file_hash'] = file_hash

                    # Add JSON path for HybridChunker
                    if json_temp_path and json_temp_path.exists():
                        doc_metadata['json_path'] = str(json_temp_path)
                        logger.info(f"   [+] JSON available for HybridChunker: {json_temp_path.name}")

                    # Create Document
                    cleaned_metadata = clean_metadata_recursive(doc_metadata)
                    document = Document(
                        id_=str(uuid.uuid4()),
                        text=content,
                        metadata=cleaned_metadata
                    )

                    documents.append(document)
                    self.loading_stats['documents_created'] += 1
                    self.loading_stats['total_characters'] += len(content)
                    self.loading_stats['registry_enrichments'] += 1

                    logger.info(f"   [OK] Loaded {original_filename} from Storage")

                except Exception as doc_err:
                    logger.error(f"   [ERR] Failed to load {original_filename}: {doc_err}")
                    self.loading_stats['failed_files'] += 1
                    continue

            logger.info(f"[+] Loaded {len(documents)} documents from Storage")
            return documents

        finally:
            # Close database connection
            try:
                if 'cur' in locals():
                    cur.close()
                if 'conn' in locals():
                    conn.close()
            except Exception as db_err:
                logger.warning(f"     Failed to close DB connection: {db_err}")

            # Cleanup temporary files
            logger.info(f"[*]   Cleaning up temporary files...")
            try:
                import shutil
                shutil.rmtree(temp_dir)
                logger.info(f"   [OK] Temporary directory cleaned")
            except Exception as cleanup_err:
                logger.warning(f"     Cleanup failed: {cleanup_err}")

    def load_data(self, registry_manager=None) -> Tuple[List[Document], Dict[str, Any]]:
        """
        Load all markdown files, enrich with JSON metadata and registry_id.
          Supports both local filesystem and Supabase Storage modes.

        Args:
            registry_manager: RegistryManager instance (optional, but recommended)

        Returns:
            Tuple of (documents, loading_stats)
        """
        start_time = time.time()
        logger.info(f"[*] Starting markdown load from: {self.input_dir}")

        if self.blacklist_directories:
            logger.info(f"[*] Blacklisted directories: {', '.join(self.blacklist_directories)}")

        if registry_manager:
            logger.info("[*] Registry enrichment: ENABLED")
        else:
            logger.warning("[!] Registry enrichment: DISABLED (registry_id will be NULL)")

        #   CHECK FOR STORAGE MODE: If storage_manager is provided, use Storage mode
        if self.storage_manager and registry_manager:
            logger.info("[*]   Detected Storage manager   Using STORAGE MODE")
            documents = self._load_from_storage(registry_manager)
            self.loading_stats['loading_time'] = time.time() - start_time
            self._print_loading_summary()
            return documents, self.loading_stats

        # Legacy: Local filesystem mode
        logger.info("[*]   Using LOCAL FILESYSTEM MODE")
        markdown_files = self._scan_markdown_files()
        
        if not markdown_files:
            logger.warning("[!] No markdown files found to load.")
            self.loading_stats['loading_time'] = time.time() - start_time
            return [], self.loading_stats

        logger.info(f"[*] Found {len(markdown_files)} markdown files. Loading content...")
        
        documents = []
        for file_path in markdown_files:
            content, error = self._read_markdown_file(file_path)
            
            if error or content is None:
                self.loading_stats['failed_files'] += 1
                self.loading_stats['failed_files_list'].append({
                    "file": file_path, 
                    "reason": error or "unknown_read_error"
                })
                logger.error(f"Failed to read {file_path}: {error}")
                continue
            
            document = self._create_document_from_markdown(file_path, content)
            
            if document:
                # Enrich with registry_id if manager provided
                if registry_manager:
                    document = self._enrich_with_registry_id(document, registry_manager)
                else:
                    logger.warning(f"[!] Document {document.metadata.get('file_name')} will NOT have registry_id")
                
                documents.append(document)
                self.loading_stats['documents_created'] += 1
                self.loading_stats['total_characters'] += len(content)
            else:
                self.loading_stats['failed_files'] += 1
                self.loading_stats['failed_files_list'].append({
                    "file": file_path, 
                    "reason": "document_creation_failed"
                })
        
        self.loading_stats['loading_time'] = time.time() - start_time
        self._print_loading_summary()
        
        return documents, self.loading_stats

    def _print_loading_summary(self):
        """Print a summary of the loading process."""
        stats = self.loading_stats
        summary = [
            "="*50,
            "[*] MARKDOWN LOADING SUMMARY",
            "="*50,
            f"[*] Loading time: {stats['loading_time']:.2f}s",
            f"[*] Markdown files found: {stats['markdown_files_found']}",
            f"[+] Documents created: {stats['documents_created']}",
            f"[-] Failed to load: {stats['failed_files']}",
            f"[*] Total characters loaded: {stats['total_characters']:,}",
            f"[*] Metadata files loaded: {stats['metadata_files_loaded']}",
            f"[?] Metadata files missing: {stats['metadata_files_missing']}",
            f"[*] Registry enrichments: {stats['registry_enrichments']}",
        ]
        
        if stats['registry_failures'] > 0:
            summary.append(f"[!] Registry failures: {stats['registry_failures']}")
        
        for line in summary:
            logger.info(line)
            
        if stats['failed_files'] > 0:
            logger.warning("--- Failed Files ---")
            for item in stats['failed_files_list'][:5]:
                logger.warning(f"  - {item['file']}: {item['reason']}")
            if len(stats['failed_files_list']) > 5:
                logger.warning(f"  ... and {len(stats['failed_files_list']) - 5} more.")
        
        # Warning if no registry enrichments
        if stats['documents_created'] > 0 and stats['registry_enrichments'] == 0:
            logger.warning("="*50)
            logger.warning("[!] WARNING: NO REGISTRY ENRICHMENTS!")
            logger.warning("Documents will be created WITHOUT registry_id")
            logger.warning("This will cause database constraint violations!")
            logger.warning("Make sure to pass registry_manager to load_data()")
            logger.warning("="*50)
        
        logger.info("="*50)

    def get_loading_stats(self):
        """Get loading statistics"""
        return self.loading_stats.copy()


def create_markdown_loader(documents_dir: str, recursive: bool = True, config: Any = None, storage_manager=None) -> MarkdownLoader:
    """
    Factory function to create a MarkdownLoader instance.
      Now supports Storage mode via storage_manager parameter.
    """
    return MarkdownLoader(
        input_dir=documents_dir,
        recursive=recursive,
        config=config,
        storage_manager=storage_manager  #   Added
    )


def validate_markdown_directory(directory_path: str) -> Tuple[bool, str, int]:
    """
    Validate that a directory exists and contains markdown files.
    """
    try:
        if not os.path.exists(directory_path):
            return False, f"Directory does not exist: {directory_path}", 0
        
        if not os.path.isdir(directory_path):
            return False, f"Path is not a directory: {directory_path}", 0
        
        markdown_count = len(list(Path(directory_path).glob("**/*.md")))
        
        if markdown_count == 0:
            return True, f"Directory is valid, but no markdown files were found in: {directory_path}", 0
        
        return True, f"Directory is valid and contains {markdown_count} markdown files.", markdown_count
        
    except Exception as e:
        return False, f"Error validating directory: {e}", 0


def scan_markdown_files(directory_path: str, recursive: bool = True) -> Dict[str, Any]:
    """
    Quick scan of markdown files in a directory.
    """
    results: Dict[str, Any] = {
        'total_markdown_files': 0,
        'total_size_bytes': 0,
        'files': []
    }
    
    try:
        glob_pattern = "**/*.md" if recursive else "*.md"
        for file_path in Path(directory_path).glob(glob_pattern):
            if file_path.is_file():
                file_size = file_path.stat().st_size
                results['total_markdown_files'] += 1
                results['total_size_bytes'] += file_size
                results['files'].append({
                    'path': str(file_path),
                    'name': file_path.name,
                    'size': file_size
                })

        if results['total_markdown_files'] > 0:
            results['average_size_bytes'] = results['total_size_bytes'] / results['total_markdown_files']
            results['total_size_mb'] = results['total_size_bytes'] / (1024 * 1024)
            
    except Exception as e:
        results['error'] = str(e)
    
    return results


def print_markdown_scan_summary(scan_results: Dict[str, Any]):
    """
    Print a summary of a markdown file scan.
    """
    if 'error' in scan_results:
        print(f"[-] Scan error: {scan_results['error']}")
        return
    
    print("\n[*] MARKDOWN FILES SCAN SUMMARY:")
    print(f"   [*] Total markdown files: {scan_results.get('total_markdown_files', 0)}")
    
    if scan_results.get('total_markdown_files', 0) > 0:
        print(f"   [*] Total size: {scan_results.get('total_size_mb', 0):.2f} MB")
        print(f"   [*] Average file size: {scan_results.get('average_size_bytes', 0) / 1024:.1f} KB")
        
        files_list = scan_results.get('files', [])
        print("\n   Files (first 10):")
        for file_info in files_list[:10]:
            size_kb = file_info.get('size', 0) / 1024
            print(f"      - {file_info.get('name')} ({size_kb:.1f} KB)")
        if len(files_list) > 10:
            print(f"      ... and {len(files_list) - 10} more.")


if __name__ == "__main__":
    # Test markdown loader when run directly
    print("[*] Markdown Loader Test (with JSON metadata and registry_id enrichment)")
    print("=" * 60)
    
    # Configure basic logging for standalone test
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Use a relative path for testing
    test_dir = str(Path(__file__).resolve().parent.parent / "data" / "markdown")
    
    is_valid, msg, file_count = validate_markdown_directory(test_dir)
    print(f"Validation result for '{test_dir}': {msg}")
    
    if is_valid and file_count > 0:
        print("\n--- Running Quick Scan ---")
        scan_results = scan_markdown_files(test_dir, recursive=True)
        print_markdown_scan_summary(scan_results)

        print("\n--- Running Full Loader Test ---")
        try:
            # Simple config mock for testing
            class MockConfig:
                BLACKLIST_DIRECTORIES = ["_metadata"]

            loader = create_markdown_loader(test_dir, config=MockConfig())
            
            # Load WITHOUT registry manager for basic test
            print("\n[!] Loading without registry_manager (registry_id will be NULL)")
            docs, stats = loader.load_data(registry_manager=None)
            
            if docs:
                print(f"\nSuccessfully loaded {len(docs)} documents.")
                print("\nVerifying metadata of the first document:")
                first_doc_meta = docs[0].metadata
                print(json.dumps(first_doc_meta, indent=2))
                
                # Check for registry_id
                if 'registry_id' in first_doc_meta:
                    print("\n[+] SUCCESS: 'registry_id' found in metadata!")
                else:
                    print("\n[!] WARNING: 'registry_id' is MISSING (expected when no registry_manager provided)")
        except Exception as e:
            print(f"\n[-] An error occurred during the full loader test: {e}")
            import traceback
            traceback.print_exc()

    print("=" * 60)