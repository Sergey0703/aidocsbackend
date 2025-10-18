#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database management module for RAG Document Indexer
Handles PostgreSQL operations, record checking, safe deletion, and end-to-end file analysis
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import sys


def get_user_confirmation(prompt, default_no=True):
    """
    Get user confirmation with default option
    
    Args:
        prompt: Question to ask user
        default_no: Whether default is No (True) or Yes (False)
    
    Returns:
        bool: User's choice
    """
    default_text = "[y/N]" if default_no else "[Y/n]"
    while True:
        response = input(f"{prompt} {default_text}: ").strip().lower()
        if response == '':
            return not default_no
        elif response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please enter 'y' for yes or 'n' for no (or press Enter for default)")


def get_files_in_database(connection_string, table_name="documents"):
    """
    Get list of files that are actually stored in the database
    
    Args:
        connection_string: PostgreSQL connection string
        table_name: Name of the documents table
    
    Returns:
        set: Set of file paths that exist in database
    """
    files_in_db = set()
    
    try:
        with psycopg2.connect(connection_string) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get all unique file paths from database
                cur.execute(f"""
                    SELECT DISTINCT metadata->>'file_path' as file_path,
                                   metadata->>'file_name' as file_name
                    FROM vecs.{table_name}
                    WHERE metadata->>'file_path' IS NOT NULL
                       OR metadata->>'file_name' IS NOT NULL
                """)
                
                results = cur.fetchall()
                
                for row in results:
                    file_path = row['file_path']
                    file_name = row['file_name']
                    
                    # Add both file_path and file_name for comparison
                    if file_path:
                        # Normalize path for comparison
                        normalized_path = os.path.normpath(os.path.abspath(file_path))
                        files_in_db.add(normalized_path)
                    
                    if file_name:
                        files_in_db.add(file_name)
                
                print(f"Found {len(files_in_db)} unique files in database")
                
    except Exception as e:
        print(f"ERROR: Could not query database for files: {e}")
    
    return files_in_db


def analyze_missing_file(file_path):
    """
    Analyze why a specific file is missing from database
    
    Args:
        file_path: Path to the missing file
    
    Returns:
        str: Detailed error description for why file didn't make it to database
    """
    file_name = os.path.basename(file_path)
    
    # Check basic file validity
    if not os.path.exists(file_path):
        return f"{file_name} - FILE_DELETED_AFTER_PROCESSING"
    
    if not os.path.isfile(file_path):
        return f"{file_name} - NOT_A_FILE"
    
    if not os.access(file_path, os.R_OK):
        return f"{file_name} - ACCESS_DENIED"
    
    # Check file size and basic properties
    try:
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return f"{file_name} - EMPTY_FILE (likely filtered out during processing)"
        elif file_size > 50 * 1024 * 1024:  # 50MB
            return f"{file_name} - FILE_TOO_LARGE ({file_size/1024/1024:.1f}MB, may have been skipped)"
    except Exception as e:
        return f"{file_name} - SIZE_CHECK_ERROR: {e}"
    
    # Check file extension
    file_ext = os.path.splitext(file_path)[1].lower()
    supported_extensions = {
        '.txt', '.pdf', '.docx', '.doc', '.pptx', '.ppt',
        '.xlsx', '.xls', '.csv', '.md', '.rtf', '.html', '.htm'
    }
    
    if file_ext not in supported_extensions:
        return f"{file_name} - UNSUPPORTED_EXTENSION: {file_ext}"
    
    # If we get here, the file looks processable but didn't make it to DB
    return f"{file_name} - PROCESSING_PIPELINE_FAILURE (file looks valid but failed somewhere in the pipeline)"


def compare_directory_with_database(directory_path, connection_string, table_name="documents", recursive=True, blacklist_directories=None):
    """
    Compare files in directory with files actually stored in database
    
    Args:
        directory_path: Path to directory containing files
        connection_string: PostgreSQL connection string
        table_name: Name of the documents table
        recursive: Whether to scan directory recursively
        blacklist_directories: List of directory names to exclude
    
    Returns:
        dict: Comprehensive comparison results
    """
    print(f"\nPerforming end-to-end analysis: Directory vs Database")
    
    # Import here to avoid circular imports
    from .file_utils_core import scan_files_in_directory
    
    # Step 1: Get all files in directory (with blacklist)
    all_files_in_dir = scan_files_in_directory(
        directory_path, 
        recursive=recursive,
        blacklist_directories=blacklist_directories,
        verbose=False
    )
    
    # Normalize all directory file paths
    normalized_dir_files = set()
    dir_file_mapping = {}  # normalized_path -> original_path
    
    for file_path in all_files_in_dir:
        normalized_path = os.path.normpath(os.path.abspath(file_path))
        normalized_dir_files.add(normalized_path)
        dir_file_mapping[normalized_path] = file_path
    
    print(f"Total files in directory: {len(normalized_dir_files)}")
    
    # Step 2: Get all files in database
    files_in_db = get_files_in_database(connection_string, table_name)
    
    # Step 3: Find files that are missing from database
    missing_files = []
    
    for normalized_path in normalized_dir_files:
        original_path = dir_file_mapping[normalized_path]
        file_name = os.path.basename(original_path)
        
        # Check if this file exists in database (by normalized path or filename)
        found_in_db = False
        
        if normalized_path in files_in_db:
            found_in_db = True
        elif file_name in files_in_db:
            found_in_db = True
        
        if not found_in_db:
            missing_files.append(original_path)
    
    print(f"Files successfully in database: {len(normalized_dir_files) - len(missing_files)}")
    print(f"Files missing from database: {len(missing_files)}")
    
    # Step 4: Analyze why each missing file didn't make it to database
    missing_files_detailed = []
    
    if missing_files:
        print(f"Analyzing {len(missing_files)} missing files...")
        
        for file_path in missing_files:
            error_detail = analyze_missing_file(file_path)
            missing_files_detailed.append(error_detail)
    
    # Prepare comprehensive results
    results = {
        'total_files_in_directory': len(normalized_dir_files),
        'files_successfully_in_db': len(normalized_dir_files) - len(missing_files),
        'files_missing_from_db': len(missing_files),
        'missing_files_detailed': missing_files_detailed,
        'success_rate': ((len(normalized_dir_files) - len(missing_files)) / len(normalized_dir_files) * 100) if len(normalized_dir_files) > 0 else 0
    }
    
    return results


class DatabaseManager:
    """Database manager for handling PostgreSQL operations"""
    
    def __init__(self, connection_string, table_name="documents"):
        """
        Initialize database manager
        
        Args:
            connection_string: PostgreSQL connection string
            table_name: Name of the documents table
        """
        self.connection_string = connection_string
        self.table_name = table_name
        self._test_connection()
    
    def _test_connection(self):
        """Test database connection and validate setup"""
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    # Test basic connection
                    cur.execute("SELECT 1")
                    
                    # Check if vecs schema exists
                    cur.execute("""
                        SELECT schema_name FROM information_schema.schemata 
                        WHERE schema_name = 'vecs'
                    """)
                    if not cur.fetchone():
                        raise Exception("Schema 'vecs' not found in database")
                    
                    # Check if table exists
                    cur.execute("""
                        SELECT table_name FROM information_schema.tables 
                        WHERE table_schema = 'vecs' AND table_name = %s
                    """, (self.table_name,))
                    if not cur.fetchone():
                        print(f"WARNING: Table 'vecs.{self.table_name}' not found - will be created automatically")
            
            print("Database connection: SUCCESS")
            
        except Exception as e:
            print(f"ERROR: Database connection failed: {e}")
            raise
    
    def get_connection(self):
        """Get a new database connection"""
        return psycopg2.connect(self.connection_string)
    
    def execute_query(self, query, params=None, fetch=False):
        """
        Execute a database query safely
        
        Args:
            query: SQL query to execute
            params: Query parameters
            fetch: Whether to fetch results
        
        Returns:
            Results if fetch=True, otherwise None
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, params)
                    if fetch:
                        return cur.fetchall()
                    return cur.rowcount
        except Exception as e:
            print(f"Database query error: {e}")
            raise
    
    def check_existing_records(self, files_to_process):
        """
        Check for existing records in database
        
        Args:
            files_to_process: Set of file identifiers to check
        
        Returns:
            tuple: (total_existing, existing_files_info)
        """
        if not files_to_process:
            return 0, []
        
        try:
            total_existing = 0
            existing_files = []
            
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    for file_identifier in files_to_process:
                        cur.execute("""
                            SELECT COUNT(*), metadata->>'file_name' 
                            FROM vecs.{} 
                            WHERE metadata->>'file_path' = %s 
                               OR metadata->>'file_name' = %s
                            GROUP BY metadata->>'file_name'
                        """.format(self.table_name), (file_identifier, file_identifier))
                        
                        results = cur.fetchall()
                        for count, filename in results:
                            total_existing += count
                            existing_files.append(f"{filename} ({count} records)")
            
            return total_existing, existing_files
            
        except Exception as e:
            print(f"Error checking existing records: {e}")
            return 0, []
    
    def delete_existing_records(self, files_to_process):
        """
        Delete existing records from database
        
        Args:
            files_to_process: Set of file identifiers to delete
        
        Returns:
            int: Number of records deleted
        """
        if not files_to_process:
            return 0
        
        try:
            deleted_count = 0
            
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    for file_identifier in files_to_process:
                        cur.execute("""
                            DELETE FROM vecs.{} 
                            WHERE metadata->>'file_path' = %s 
                               OR metadata->>'file_name' = %s
                        """.format(self.table_name), (file_identifier, file_identifier))
                        deleted_count += cur.rowcount
                
                conn.commit()
            
            return deleted_count
            
        except Exception as e:
            print(f"Error deleting existing records: {e}")
            return 0
    
    def get_database_stats(self):
        """
        Get database statistics
        
        Returns:
            dict: Database statistics
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Total records
                    cur.execute(f"SELECT COUNT(*) as total FROM vecs.{self.table_name}")
                    total_records = cur.fetchone()['total']
                    
                    # Table size
                    cur.execute("""
                        SELECT 
                            pg_size_pretty(pg_total_relation_size('vecs.{}')) as table_size,
                            pg_size_pretty(pg_database_size(current_database())) as db_size
                    """.format(self.table_name))
                    sizes = cur.fetchone()
                    
                    # Recent activity
                    cur.execute("""
                        SELECT 
                            metadata->>'indexed_at' as indexed_date,
                            COUNT(*) as count
                        FROM vecs.{}
                        WHERE metadata->>'indexed_at' IS NOT NULL
                        GROUP BY metadata->>'indexed_at'
                        ORDER BY metadata->>'indexed_at' DESC
                        LIMIT 5
                    """.format(self.table_name))
                    recent_activity = cur.fetchall()
                    
                    return {
                        'total_records': total_records,
                        'table_size': sizes['table_size'],
                        'database_size': sizes['db_size'],
                        'recent_activity': recent_activity
                    }
                    
        except Exception as e:
            print(f"Error getting database stats: {e}")
            return {'error': str(e)}
    
    def safe_deletion_dialog(self, files_to_process, incremental_mode=False):
        """
        Safe deletion dialog with user confirmation
        
        Args:
            files_to_process: Set of file identifiers to process
            incremental_mode: If True, skip deletion check for new files
        
        Returns:
            dict: Deletion information
        """
        deletion_info = {'files_processed': 0, 'records_deleted': 0}
        
        if not files_to_process:
            print("SUCCESS: No files to process")
            return deletion_info
        
        # In incremental mode, skip deletion check - only new files are being processed
        if incremental_mode:
            print("INFO: Incremental mode - skipping deletion check (processing only new/modified files)")
            deletion_info = {
                'files_processed': len(files_to_process),
                'records_deleted': 'Skipped in incremental mode'
            }
            return deletion_info
        
        # Check existing records (only in non-incremental mode)
        total_existing, existing_files = self.check_existing_records(files_to_process)
        
        if total_existing == 0:
            print("SUCCESS: No existing records found - proceeding with clean indexing")
            deletion_info = {
                'files_processed': len(files_to_process),
                'records_deleted': 'No existing records'
            }
            return deletion_info
        
        # Show existing records information
        print(f"\nWARNING: EXISTING RECORDS DETECTED")
        print(f"Found {total_existing} existing records for {len(files_to_process)} files")
        
        if len(existing_files) <= 10:
            print("\nExisting files:")
            for file_info in existing_files:
                print(f"  * {file_info}")
        else:
            print(f"\nFirst 10 existing files:")
            for file_info in existing_files[:10]:
                print(f"  * {file_info}")
            print(f"  ... and {len(existing_files) - 10} more files")
        
        # Show options
        print(f"\nAVAILABLE OPTIONS:")
        print("1. DELETE existing records and reindex")
        print("2. SKIP deletion and add new records") 
        print("3. ABORT indexing")
        
        if total_existing > 1000:
            print(f"\nWARNING: {total_existing} records is a large number!")
        
        # Get user choice
        while True:
            choice = input(f"\nChoose option (1/2/3) [default: 2 - skip deletion]: ").strip()
            
            if choice == '' or choice == '2':
                print("SUCCESS: Skipping deletion - will add new records alongside existing ones")
                deletion_info = {
                    'files_processed': len(files_to_process),
                    'records_deleted': 'Skipped by user choice'
                }
                break
                
            elif choice == '1':
                # Confirm deletion if large number of records
                if total_existing > 100:
                    confirm = get_user_confirmation(
                        f"WARNING: Really delete {total_existing} records? This cannot be undone!", 
                        default_no=True
                    )
                    if not confirm:
                        print("ERROR: Deletion cancelled")
                        continue
                
                print("INFO: Proceeding with deletion...")
                deleted_count = self.delete_existing_records(files_to_process)
                
                if deleted_count > 0:
                    print(f"SUCCESS: Successfully deleted {deleted_count} existing records")
                else:
                    print("WARNING: No records were deleted (possible error)")
                
                deletion_info = {
                    'files_processed': len(files_to_process),
                    'records_deleted': deleted_count
                }
                break
                
            elif choice == '3':
                print("ERROR: Indexing aborted by user")
                sys.exit(0)
                
            else:
                print("ERROR: Invalid choice. Please enter 1, 2, or 3")
        
        return deletion_info
    
    def validate_embeddings(self, expected_dimension=1024):
        """
        Validate embeddings in database
        
        Args:
            expected_dimension: Expected embedding dimension
        
        Returns:
            dict: Validation results
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Check embedding dimensions
                    cur.execute("""
                        SELECT 
                            array_length(embedding, 1) as dimension,
                            COUNT(*) as count,
                            ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM vecs.{}), 2) as percentage
                        FROM vecs.{}
                        WHERE embedding IS NOT NULL
                        GROUP BY array_length(embedding, 1)
                        ORDER BY count DESC
                    """.format(self.table_name, self.table_name))
                    
                    dimensions = cur.fetchall()
                    
                    # Check for null embeddings
                    cur.execute(f"""
                        SELECT COUNT(*) as null_embeddings 
                        FROM vecs.{self.table_name} 
                        WHERE embedding IS NULL
                    """)
                    null_count = cur.fetchone()['null_embeddings']
                    
                    return {
                        'dimensions': dimensions,
                        'null_embeddings': null_count,
                        'expected_dimension': expected_dimension,
                        'has_correct_dimension': any(d['dimension'] == expected_dimension for d in dimensions)
                    }
                    
        except Exception as e:
            return {'error': str(e)}
    
    def cleanup_orphaned_records(self, file_paths_to_keep=None):
        """
        Clean up orphaned records (files that no longer exist)
        
        Args:
            file_paths_to_keep: Set of file paths that should be kept
        
        Returns:
            int: Number of records cleaned up
        """
        if file_paths_to_keep is None:
            print("WARNING: No file paths provided - skipping cleanup")
            return 0
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Find records with file paths not in the keep list
                    placeholders = ','.join(['%s'] * len(file_paths_to_keep))
                    cur.execute(f"""
                        SELECT COUNT(*) FROM vecs.{self.table_name}
                        WHERE metadata->>'file_path' NOT IN ({placeholders})
                    """, list(file_paths_to_keep))
                    
                    orphaned_count = cur.fetchone()[0]
                    
                    if orphaned_count > 0:
                        confirm = get_user_confirmation(
                            f"Found {orphaned_count} orphaned records. Delete them?",
                            default_no=True
                        )
                        
                        if confirm:
                            cur.execute(f"""
                                DELETE FROM vecs.{self.table_name}
                                WHERE metadata->>'file_path' NOT IN ({placeholders})
                            """, list(file_paths_to_keep))
                            
                            deleted_count = cur.rowcount
                            conn.commit()
                            
                            print(f"SUCCESS: Cleaned up {deleted_count} orphaned records")
                            return deleted_count
                    
                    return 0
                    
        except Exception as e:
            print(f"Error during cleanup: {e}")
            return 0
    
    def print_database_info(self):
        """Print comprehensive database information"""
        print("\n" + "="*50)
        print("DATABASE INFORMATION")
        print("="*50)
        
        stats = self.get_database_stats()
        if 'error' in stats:
            print(f"Error getting stats: {stats['error']}")
            return
        
        print(f"Table: vecs.{self.table_name}")
        print(f"Total records: {stats['total_records']:,}")
        print(f"Table size: {stats['table_size']}")
        print(f"Database size: {stats['database_size']}")
        
        if stats['recent_activity']:
            print(f"\nRecent indexing activity:")
            for activity in stats['recent_activity']:
                print(f"  {activity['indexed_date']}: {activity['count']} records")
        
        # Validate embeddings
        validation = self.validate_embeddings()
        if 'error' not in validation:
            print(f"\nEmbedding validation:")
            if validation['dimensions']:
                for dim_info in validation['dimensions']:
                    status = "OK" if dim_info['dimension'] == validation['expected_dimension'] else "WARNING"
                    print(f"  {dim_info['dimension']}D: {dim_info['count']} records ({dim_info['percentage']}%) [{status}]")
            
            if validation['null_embeddings'] > 0:
                print(f"  NULL embeddings: {validation['null_embeddings']} records")
        
        print("="*50)
    
    def analyze_directory_vs_database(self, directory_path, recursive=True, blacklist_directories=None):
        """
        Perform end-to-end analysis comparing directory with database
        
        Args:
            directory_path: Path to directory to analyze
            recursive: Whether to scan recursively
            blacklist_directories: List of directory names to exclude
        
        Returns:
            dict: Analysis results
        """
        return compare_directory_with_database(
            directory_path, 
            self.connection_string, 
            self.table_name, 
            recursive,
            blacklist_directories
        )


def create_database_manager(connection_string, table_name="documents"):
    """
    Create a database manager instance
    
    Args:
        connection_string: PostgreSQL connection string
        table_name: Name of the documents table
    
    Returns:
        DatabaseManager: Configured database manager
    """
    return DatabaseManager(connection_string, table_name)