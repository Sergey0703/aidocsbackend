#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FIXED: Database integration with document registry
Handles registry_id creation and proper foreign key relationships
"""

import uuid
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from pathlib import Path


class RegistryManager:
    """Manages document registry operations"""
    
    def __init__(self, connection_string):
        self.connection_string = connection_string
    
    def get_or_create_registry_entry(self, file_path, metadata=None):
        """
        Get existing or create new registry entry for a file
        
        Args:
            file_path: Path to the file
            metadata: Optional metadata dict
        
        Returns:
            UUID: registry_id
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Normalize file path
                    normalized_path = str(Path(file_path).resolve())
                    
                    # Check if registry entry exists
                    cur.execute("""
                        SELECT id FROM vecs.document_registry 
                        WHERE file_path = %s
                    """, (normalized_path,))
                    
                    result = cur.fetchone()
                    
                    if result:
                        # Update existing entry
                        registry_id = result['id']
                        cur.execute("""
                            UPDATE vecs.document_registry 
                            SET updated_at = now(),
                                extracted_data = COALESCE(%s::jsonb, extracted_data)
                            WHERE id = %s
                        """, (metadata, registry_id))
                        print(f"   INFO: Using existing registry entry: {registry_id}")
                    else:
                        # Create new registry entry
                        registry_id = uuid.uuid4()
                        
                        # Extract document type from file extension
                        file_ext = Path(file_path).suffix.lower()
                        doc_type_map = {
                            '.pdf': 'pdf',
                            '.docx': 'word',
                            '.doc': 'word',
                            '.md': 'markdown',
                            '.txt': 'text',
                            '.xlsx': 'excel',
                            '.xls': 'excel'
                        }
                        document_type = doc_type_map.get(file_ext, 'other')
                        
                        cur.execute("""
                            INSERT INTO vecs.document_registry 
                            (id, file_path, document_type, status, extracted_data)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (
                            registry_id,
                            normalized_path,
                            document_type,
                            'indexed',
                            metadata
                        ))
                        print(f"   INFO: Created new registry entry: {registry_id}")
                    
                    conn.commit()
                    return registry_id
                    
        except Exception as e:
            print(f"   ERROR: Failed to get/create registry entry: {e}")
            raise
    
    def batch_create_registry_entries(self, file_paths_with_metadata):
        """
        Batch create registry entries for multiple files
        
        Args:
            file_paths_with_metadata: List of (file_path, metadata) tuples
        
        Returns:
            dict: Mapping of file_path to registry_id
        """
        registry_map = {}
        
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    for file_path, metadata in file_paths_with_metadata:
                        normalized_path = str(Path(file_path).resolve())
                        
                        # Check existing
                        cur.execute("""
                            SELECT id FROM vecs.document_registry 
                            WHERE file_path = %s
                        """, (normalized_path,))
                        
                        result = cur.fetchone()
                        
                        if result:
                            registry_id = result['id']
                        else:
                            # Create new
                            registry_id = uuid.uuid4()
                            file_ext = Path(file_path).suffix.lower()
                            doc_type_map = {
                                '.pdf': 'pdf', '.docx': 'word', '.doc': 'word',
                                '.md': 'markdown', '.txt': 'text',
                                '.xlsx': 'excel', '.xls': 'excel'
                            }
                            document_type = doc_type_map.get(file_ext, 'other')
                            
                            cur.execute("""
                                INSERT INTO vecs.document_registry 
                                (id, file_path, document_type, status, extracted_data)
                                VALUES (%s, %s, %s, %s, %s)
                            """, (
                                registry_id,
                                normalized_path,
                                document_type,
                                'indexed',
                                metadata
                            ))
                        
                        registry_map[normalized_path] = str(registry_id)
                    
                    conn.commit()
                    
        except Exception as e:
            print(f"   ERROR: Batch registry creation failed: {e}")
            raise
        
        return registry_map


def enhance_nodes_with_registry_id(nodes, registry_manager):
    """
    Enhance nodes with registry_id before saving to database
    
    Args:
        nodes: List of nodes to enhance
        registry_manager: RegistryManager instance
    
    Returns:
        List of enhanced nodes
    """
    print(f"   INFO: Enhancing {len(nodes)} nodes with registry_id...")
    
    # Group nodes by file_path
    file_groups = {}
    for node in nodes:
        file_path = node.metadata.get('file_path')
        if not file_path:
            print(f"   WARNING: Node missing file_path in metadata, skipping")
            continue
        
        if file_path not in file_groups:
            file_groups[file_path] = []
        file_groups[file_path].append(node)
    
    # Create registry entries for all unique files
    files_with_metadata = []
    for file_path, file_nodes in file_groups.items():
        # Use metadata from first node as representative
        first_node_metadata = {
            'file_name': file_nodes[0].metadata.get('file_name'),
            'file_type': file_nodes[0].metadata.get('file_type'),
            'file_size': file_nodes[0].metadata.get('file_size'),
            'total_chunks': len(file_nodes),
            'indexed_at': datetime.now().isoformat()
        }
        files_with_metadata.append((file_path, first_node_metadata))
    
    # Batch create registry entries
    registry_map = registry_manager.batch_create_registry_entries(files_with_metadata)
    
    # Enhance all nodes with their registry_id
    enhanced_nodes = []
    nodes_without_registry = 0
    
    for node in nodes:
        file_path = node.metadata.get('file_path')
        if not file_path:
            nodes_without_registry += 1
            continue
        
        normalized_path = str(Path(file_path).resolve())
        registry_id = registry_map.get(normalized_path)
        
        if registry_id:
            # Add registry_id to metadata
            node.metadata['registry_id'] = registry_id
            enhanced_nodes.append(node)
        else:
            print(f"   WARNING: No registry_id found for {file_path}")
            nodes_without_registry += 1
    
    print(f"   INFO: Enhanced {len(enhanced_nodes)} nodes with registry_id")
    if nodes_without_registry > 0:
        print(f"   WARNING: {nodes_without_registry} nodes could not be enhanced")
    
    return enhanced_nodes


def save_nodes_with_registry(nodes, vector_store, connection_string, batch_size=25):
    """
    Save nodes to database with proper registry_id handling
    
    Args:
        nodes: List of nodes to save
        vector_store: Vector store instance
        connection_string: PostgreSQL connection string
        batch_size: Batch size for saving
    
    Returns:
        int: Number of successfully saved nodes
    """
    from .embedding_processor import aggressive_clean_all_nodes
    
    print(f"   INFO: Preparing to save {len(nodes)} nodes with registry support...")
    
    # Step 1: Create registry manager
    registry_manager = RegistryManager(connection_string)
    
    # Step 2: Enhance nodes with registry_id
    enhanced_nodes = enhance_nodes_with_registry_id(nodes, registry_manager)
    
    if not enhanced_nodes:
        print(f"   ERROR: No nodes could be enhanced with registry_id")
        return 0
    
    # Step 3: Clean nodes before saving
    print(f"   INFO: Cleaning {len(enhanced_nodes)} nodes from null bytes...")
    cleaned_nodes = aggressive_clean_all_nodes(enhanced_nodes)
    
    # Step 4: Save to database
    try:
        # Use custom SQL to insert with registry_id
        saved_count = save_with_custom_sql(cleaned_nodes, connection_string, batch_size)
        print(f"   SUCCESS: Saved {saved_count} nodes to database")
        return saved_count
        
    except Exception as e:
        print(f"   ERROR: Failed to save nodes: {e}")
        return 0


def save_with_custom_sql(nodes, connection_string, batch_size=25):
    """
    Save nodes using custom SQL that includes registry_id
    
    Args:
        nodes: List of cleaned nodes with registry_id
        connection_string: PostgreSQL connection string
        batch_size: Batch size for insertion
    
    Returns:
        int: Number of saved nodes
    """
    saved_count = 0
    
    try:
        with psycopg2.connect(connection_string) as conn:
            with conn.cursor() as cur:
                # Process in batches
                for i in range(0, len(nodes), batch_size):
                    batch = nodes[i:i + batch_size]
                    
                    for node in batch:
                        # Extract data from node
                        node_id = uuid.uuid4() if not hasattr(node, 'id_') else node.id_
                        registry_id = node.metadata.get('registry_id')
                        
                        if not registry_id:
                            print(f"   WARNING: Node missing registry_id, skipping")
                            continue
                        
                        # Get embedding
                        embedding = node.embedding if hasattr(node, 'embedding') else None
                        if embedding is None:
                            print(f"   WARNING: Node missing embedding, skipping")
                            continue
                        
                        # Prepare metadata (exclude registry_id as it's a separate column)
                        metadata = {k: v for k, v in node.metadata.items() if k != 'registry_id'}
                        
                        # Insert with registry_id
                        cur.execute("""
                            INSERT INTO vecs.documents (id, registry_id, vec, metadata)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (id) DO UPDATE 
                            SET vec = EXCLUDED.vec, 
                                metadata = EXCLUDED.metadata,
                                registry_id = EXCLUDED.registry_id
                        """, (
                            str(node_id),
                            registry_id,
                            embedding,
                            metadata
                        ))
                        
                        saved_count += 1
                    
                    conn.commit()
                    
                    if (i // batch_size + 1) % 10 == 0:
                        print(f"   INFO: Saved {saved_count}/{len(nodes)} nodes...")
        
        return saved_count
        
    except Exception as e:
        print(f"   ERROR: Custom SQL save failed: {e}")
        raise


# Integration function for embedding_processor.py
def integrate_with_embedding_processor(processor, connection_string):
    """
    Integrate registry support into existing EmbeddingProcessor
    
    Args:
        processor: EmbeddingProcessor instance
        connection_string: PostgreSQL connection string
    
    Returns:
        Modified processor with registry support
    """
    # Store original save method
    original_save_method = processor.robust_save_to_database
    
    # Create wrapper that adds registry support
    def enhanced_save_method(nodes_with_embeddings, batch_num, db_batch_size=25):
        """Enhanced save method with registry support"""
        return save_nodes_with_registry(
            nodes_with_embeddings,
            processor.vector_store,
            connection_string,
            db_batch_size
        )
    
    # Replace save method
    processor.robust_save_to_database = enhanced_save_method
    processor.registry_enabled = True
    
    print("   INFO: Registry support integrated into EmbeddingProcessor")
    
    return processor


if __name__ == "__main__":
    print("Registry Manager Test")
    print("=" * 60)
    
    # This is a test/example - you'll need to provide your connection string
    test_connection_string = "postgresql://user:pass@localhost:5432/dbname"
    
    try:
        manager = RegistryManager(test_connection_string)
        print("[+] RegistryManager initialized successfully")
        
        # Test registry entry creation
        test_file = "/path/to/test.pdf"
        test_metadata = {"test": "data"}
        
        registry_id = manager.get_or_create_registry_entry(test_file, test_metadata)
        print(f"[+] Created/retrieved registry entry: {registry_id}")
        
    except Exception as e:
        print(f"[-] Test failed: {e}")