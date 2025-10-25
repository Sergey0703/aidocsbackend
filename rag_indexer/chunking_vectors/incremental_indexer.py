#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Incremental indexer module for RAG Document Indexer
Tracks indexed files and processes only new/modified documents
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime


class IncrementalIndexer:
    """Manages incremental indexing state"""
    
    def __init__(self, config, db_manager):
        """
        Initialize incremental indexer
        
        Args:
            config: Configuration object
            db_manager: Database manager instance
        """
        self.config = config
        self.db_manager = db_manager
        
        # State file location
        self.state_dir = Path("./data/indexing_state")
        self.state_file = self.state_dir / "indexed_files.json"
        
        # Ensure state directory exists
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing state
        self.indexed_files = self._load_state()
    
    def _load_state(self):
        """
        Load indexing state from file
        
        Returns:
            dict: State dictionary
        """
        if not self.state_file.exists():
            print("[*] No previous indexing state found (first run)")
            return {}
        
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            print(f"[*] Loaded state: {len(state)} previously indexed files")
            return state
            
        except Exception as e:
            print(f"[!] Could not load state file: {e}")
            return {}
    
    def _save_state(self):
        """Save indexing state to file"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.indexed_files, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[!] Could not save state file: {e}")
            return False
    
    def _calculate_file_hash(self, file_path):
        """
        Calculate SHA256 hash of file content
        
        Args:
            file_path: Path to file
        
        Returns:
            str: File hash
        """
        sha256_hash = hashlib.sha256()
        
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            print(f"[!] Could not hash {file_path}: {e}")
            return None
    
    def get_file_info(self, file_path):
        """
        Get file information for tracking
        
        Args:
            file_path: Path to file
        
        Returns:
            dict: File information
        """
        file_path = Path(file_path)
        
        try:
            stat = file_path.stat()
            
            return {
                'path': str(file_path),
                'size': stat.st_size,
                'modified': stat.st_mtime,
                'hash': self._calculate_file_hash(file_path),
                'indexed_at': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"[!] Could not get file info for {file_path}: {e}")
            return None
    
    def is_file_indexed(self, file_path):
        """
        Check if file was already indexed
        
        Args:
            file_path: Path to file
        
        Returns:
            bool: True if already indexed and unchanged
        """
        file_path_str = str(Path(file_path))
        
        # Not in state = not indexed
        if file_path_str not in self.indexed_files:
            return False
        
        # Get stored info
        stored_info = self.indexed_files[file_path_str]
        
        # Get current info
        current_info = self.get_file_info(file_path)
        if not current_info:
            return False
        
        # Compare hash (most reliable)
        if stored_info.get('hash') and current_info.get('hash'):
            return stored_info['hash'] == current_info['hash']
        
        # Fallback: compare size and modification time
        return (stored_info.get('size') == current_info.get('size') and
                stored_info.get('modified') == current_info.get('modified'))
    
    def filter_new_and_modified(self, documents):
        """
        Filter documents to only new and modified ones
        
        Args:
            documents: List of Document objects
        
        Returns:
            tuple: (new_documents, modified_documents, unchanged_documents)
        """
        new_docs = []
        modified_docs = []
        unchanged_docs = []
        
        print("\n[*] Checking for new/modified files...")
        
        for doc in documents:
            file_path = doc.metadata.get('file_path')
            
            if not file_path:
                # No path in metadata, treat as new
                new_docs.append(doc)
                continue
            
            if not self.is_file_indexed(file_path):
                # Check if file exists in database but not in state
                if self._exists_in_database(file_path):
                    modified_docs.append(doc)
                else:
                    new_docs.append(doc)
            else:
                unchanged_docs.append(doc)
        
        print(f"     New files: {len(new_docs)}")
        print(f"   [*] Modified files: {len(modified_docs)}")
        print(f"   [+] Unchanged files: {len(unchanged_docs)}")
        
        return new_docs, modified_docs, unchanged_docs
    
    def _exists_in_database(self, file_path):
        """
        Check if file exists in database
        
        Args:
            file_path: Path to file
        
        Returns:
            bool: True if exists in database
        """
        try:
            # Get files from database
            files_in_db = self.db_manager.get_files_in_database() if hasattr(self.db_manager, 'get_files_in_database') else set()
            
            # Normalize path for comparison
            file_name = Path(file_path).name
            
            return file_name in files_in_db or str(file_path) in files_in_db
            
        except Exception as e:
            print(f"[!] Could not check database: {e}")
            return False
    
    def mark_as_indexed(self, file_path):
        """
        Mark a file as indexed
        
        Args:
            file_path: Path to file
        """
        file_info = self.get_file_info(file_path)
        
        if file_info:
            self.indexed_files[str(Path(file_path))] = file_info
    
    def mark_batch_as_indexed(self, documents):
        """
        Mark a batch of documents as indexed
        
        Args:
            documents: List of Document objects
        """
        print("\n[*] Updating indexing state...")
        
        count = 0
        for doc in documents:
            file_path = doc.metadata.get('file_path')
            if file_path:
                self.mark_as_indexed(file_path)
                count += 1
        
        # Save state
        if self._save_state():
            print(f"   [+] Saved state for {count} files")
        else:
            print(f"   [!] Could not save state")
    
    def remove_deleted_files(self):
        """
        Remove deleted files from state and database
        
        Returns:
            dict: Cleanup statistics
        """
        print("\n[*] Checking for deleted files...")
        
        deleted_count = 0
        files_to_remove = []
        
        # Check each file in state
        for file_path in list(self.indexed_files.keys()):
            if not Path(file_path).exists():
                files_to_remove.append(file_path)
                deleted_count += 1
        
        if deleted_count == 0:
            print("   [+] No deleted files found")
            return {'deleted': 0}
        
        print(f"   Found {deleted_count} deleted files")
        
        # Remove from state
        for file_path in files_to_remove:
            del self.indexed_files[file_path]
        
        # Save updated state
        self._save_state()
        
        # Remove from database (if database manager supports it)
        db_removed = 0
        if hasattr(self.db_manager, 'delete_by_file_paths'):
            try:
                db_removed = self.db_manager.delete_by_file_paths(files_to_remove)
                print(f"   [*] Removed {db_removed} records from database")
            except Exception as e:
                print(f"   [!] Could not remove from database: {e}")
        
        return {
            'deleted': deleted_count,
            'db_removed': db_removed,
            'files': files_to_remove
        }
    
    def get_statistics(self):
        """
        Get indexing statistics
        
        Returns:
            dict: Statistics
        """
        total_indexed = len(self.indexed_files)
        
        # Calculate total size
        total_size = sum(info.get('size', 0) for info in self.indexed_files.values())
        
        # Get oldest and newest
        if self.indexed_files:
            dates = [info.get('indexed_at', '') for info in self.indexed_files.values() if info.get('indexed_at')]
            oldest = min(dates) if dates else None
            newest = max(dates) if dates else None
        else:
            oldest = newest = None
        
        return {
            'total_indexed_files': total_indexed,
            'total_size_bytes': total_size,
            'total_size_mb': total_size / (1024 * 1024),
            'oldest_indexed': oldest,
            'newest_indexed': newest,
            'state_file': str(self.state_file)
        }
    
    def print_statistics(self):
        """Print indexing statistics"""
        stats = self.get_statistics()
        
        print("\n[*] Indexing State Statistics:")
        print(f"   Total indexed files: {stats['total_indexed_files']}")
        print(f"   Total size: {stats['total_size_mb']:.1f} MB")
        
        if stats['oldest_indexed']:
            print(f"   Oldest: {stats['oldest_indexed'][:10]}")
        if stats['newest_indexed']:
            print(f"   Newest: {stats['newest_indexed'][:10]}")
        
        print(f"   State file: {stats['state_file']}")
    
    def reset_state(self):
        """Reset indexing state (delete state file)"""
        try:
            if self.state_file.exists():
                self.state_file.unlink()
                print("[+] Indexing state reset")
            self.indexed_files = {}
            return True
        except Exception as e:
            print(f"[-] Could not reset state: {e}")
            return False


def create_incremental_indexer(config, db_manager):
    """
    Create incremental indexer instance
    
    Args:
        config: Configuration object
        db_manager: Database manager instance
    
    Returns:
        IncrementalIndexer: Incremental indexer instance
    """
    return IncrementalIndexer(config, db_manager)