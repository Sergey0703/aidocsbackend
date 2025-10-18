#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Metadata Inspector
Checks what metadata is currently stored in the database for existing records

This script examines the metadata structure of existing records to understand:
- What file information is already being stored
- The format and completeness of metadata fields
- Whether incremental update logic is feasible with existing data
"""

import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from datetime import datetime


def connect_to_database():
    """
    Connect to the database using environment variables
    
    Returns:
        psycopg2.connection: Database connection or None if failed
    """
    load_dotenv()
    
    connection_string = os.getenv("SUPABASE_CONNECTION_STRING")
    if not connection_string:
        print("ERROR: SUPABASE_CONNECTION_STRING not found in .env file!")
        return None
    
    try:
        conn = psycopg2.connect(connection_string)
        print("? Database connection successful")
        return conn
    except Exception as e:
        print(f"? Database connection failed: {e}")
        return None


def analyze_metadata_structure(metadata_samples):
    """
    Analyze the structure and completeness of metadata samples
    
    Args:
        metadata_samples: List of metadata dictionaries
    
    Returns:
        dict: Analysis results
    """
    if not metadata_samples:
        return {"error": "No metadata samples provided"}
    
    # Collect all unique keys across all samples
    all_keys = set()
    for metadata in metadata_samples:
        if isinstance(metadata, dict):
            all_keys.update(metadata.keys())
    
    # Analyze each key
    key_analysis = {}
    for key in all_keys:
        key_info = {
            'present_in_samples': 0,
            'sample_values': [],
            'value_types': set(),
            'is_file_related': key in ['file_path', 'file_name', 'file_size', 'file_type', 
                                     'creation_date', 'last_modified_date', 'last_accessed_date'],
            'is_content_related': key in ['text', 'content_length', 'word_count', 'paragraph_count'],
            'is_processing_related': key in ['indexed_at', 'quality_score', 'encoding_method', 'ocr_extracted']
        }
        
        for metadata in metadata_samples:
            if isinstance(metadata, dict) and key in metadata:
                key_info['present_in_samples'] += 1
                value = metadata[key]
                key_info['sample_values'].append(str(value)[:100])  # Truncate long values
                key_info['value_types'].add(type(value).__name__)
        
        key_analysis[key] = key_info
    
    return {
        'total_unique_keys': len(all_keys),
        'key_analysis': key_analysis,
        'samples_analyzed': len(metadata_samples)
    }


def check_database_metadata():
    """
    Check metadata structure in the database
    """
    print("?? Database Metadata Inspector")
    print("=" * 50)
    
    # Connect to database
    conn = connect_to_database()
    if not conn:
        return
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get table name from environment or use default
            table_name = os.getenv("TABLE_NAME", "documents")
            
            # Get basic table info
            cur.execute(f"""
                SELECT COUNT(*) as total_records
                FROM vecs.{table_name}
            """)
            total_records = cur.fetchone()['total_records']
            print(f"?? Total records in table: {total_records:,}")
            
            if total_records == 0:
                print("?? No records found in the database")
                return
            
            # Get first few records with their metadata
            sample_size = min(5, total_records)  # Check up to 5 records
            print(f"?? Analyzing metadata from first {sample_size} records...")
            print()
            
            cur.execute(f"""
                SELECT 
                    id,
                    metadata
                FROM vecs.{table_name}
                ORDER BY id
                LIMIT {sample_size}
            """)
            
            records = cur.fetchall()
            metadata_samples = []
            
            # Display each record's metadata
            for i, record in enumerate(records, 1):
                print(f"?? RECORD {i}:")
                print(f"   ID: {record['id']}")
                
                metadata = record['metadata']
                if metadata:
                    metadata_samples.append(metadata)
                    
                    # Pretty print metadata
                    print("   Metadata:")
                    for key, value in metadata.items():
                        # Truncate long values for display
                        if isinstance(value, str) and len(value) > 100:
                            display_value = value[:97] + "..."
                        else:
                            display_value = value
                        print(f"     {key}: {display_value}")
                else:
                    print("   Metadata: None")
                
                print()
            
            # Analyze metadata structure
            print("?? METADATA ANALYSIS:")
            print("=" * 50)
            
            analysis = analyze_metadata_structure(metadata_samples)
            
            if 'error' in analysis:
                print(f"? Analysis error: {analysis['error']}")
                return
            
            print(f"?? Total unique metadata keys found: {analysis['total_unique_keys']}")
            print(f"?? Samples analyzed: {analysis['samples_analyzed']}")
            print()
            
            # Categorize keys
            file_keys = []
            content_keys = []
            processing_keys = []
            other_keys = []
            
            for key, info in analysis['key_analysis'].items():
                if info['is_file_related']:
                    file_keys.append(key)
                elif info['is_content_related']:
                    content_keys.append(key)
                elif info['is_processing_related']:
                    processing_keys.append(key)
                else:
                    other_keys.append(key)
            
            # Display categorized results
            print("?? FILE-RELATED METADATA:")
            if file_keys:
                for key in sorted(file_keys):
                    info = analysis['key_analysis'][key]
                    presence = f"{info['present_in_samples']}/{analysis['samples_analyzed']}"
                    types = ", ".join(info['value_types'])
                    print(f"   ? {key}: present in {presence} samples, types: {types}")
                    
                    # Show sample values for important keys
                    if key in ['file_size', 'last_modified_date', 'creation_date'] and info['sample_values']:
                        print(f"      Sample: {info['sample_values'][0]}")
            else:
                print("   ? No file-related metadata found")
            
            print()
            print("?? CONTENT-RELATED METADATA:")
            if content_keys:
                for key in sorted(content_keys):
                    info = analysis['key_analysis'][key]
                    presence = f"{info['present_in_samples']}/{analysis['samples_analyzed']}"
                    types = ", ".join(info['value_types'])
                    print(f"   ? {key}: present in {presence} samples, types: {types}")
            else:
                print("   ? No content-related metadata found")
            
            print()
            print("?? PROCESSING-RELATED METADATA:")
            if processing_keys:
                for key in sorted(processing_keys):
                    info = analysis['key_analysis'][key]
                    presence = f"{info['present_in_samples']}/{analysis['samples_analyzed']}"
                    types = ", ".join(info['value_types'])
                    print(f"   ? {key}: present in {presence} samples, types: {types}")
            else:
                print("   ? No processing-related metadata found")
            
            if other_keys:
                print()
                print("?? OTHER METADATA:")
                for key in sorted(other_keys):
                    info = analysis['key_analysis'][key]
                    presence = f"{info['present_in_samples']}/{analysis['samples_analyzed']}"
                    types = ", ".join(info['value_types'])
                    print(f"   ?? {key}: present in {presence} samples, types: {types}")
            
            # Recommendations
            print()
            print("?? RECOMMENDATIONS FOR INCREMENTAL UPDATES:")
            print("=" * 50)
            
            required_keys = ['file_path', 'file_size', 'last_modified_date']
            missing_keys = [key for key in required_keys if key not in file_keys]
            
            if missing_keys:
                print("? MISSING REQUIRED METADATA for incremental updates:")
                for key in missing_keys:
                    print(f"   - {key}")
                print()
                print("?? ACTION NEEDED: Update indexing process to include missing metadata")
            else:
                print("? All required metadata present for incremental updates!")
                print("?? You can implement incremental update logic based on:")
                print("   - file_path (to identify files)")
                print("   - file_size (to detect changes)")
                print("   - last_modified_date (to detect updates)")
            
            # Check date formats
            if 'last_modified_date' in file_keys:
                date_samples = []
                for metadata in metadata_samples:
                    if 'last_modified_date' in metadata:
                        date_samples.append(metadata['last_modified_date'])
                
                if date_samples:
                    print()
                    print("?? DATE FORMAT ANALYSIS:")
                    print(f"   Sample dates: {date_samples[:3]}")
                    
                    # Try to parse dates
                    parseable_count = 0
                    for date_str in date_samples:
                        try:
                            # Try ISO format first
                            datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
                            parseable_count += 1
                        except:
                            try:
                                # Try other common formats
                                datetime.strptime(str(date_str), '%Y-%m-%d')
                                parseable_count += 1
                            except:
                                pass
                    
                    if parseable_count == len(date_samples):
                        print("   ? All dates are parseable")
                    else:
                        print(f"   ?? {len(date_samples) - parseable_count}/{len(date_samples)} dates may need format standardization")
            
    except Exception as e:
        print(f"? Error analyzing database: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()
        print()
        print("?? Database connection closed")


if __name__ == "__main__":
    try:
        check_database_metadata()
    except KeyboardInterrupt:
        print("\n?? Metadata check interrupted by user")
    except Exception as e:
        print(f"\n? Unexpected error: {e}")
        import traceback
        traceback.print_exc()