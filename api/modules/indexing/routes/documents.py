#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# api/modules/indexing/routes/documents.py
# Real implementation with DocumentService integration

import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional

from ..models.schemas import (
    DocumentListResponse,
    DocumentDetailResponse,
    DocumentStatsResponse,
    DeleteDocumentResponse,
    MissingDocumentsResponse,
    DocumentSearchRequest,
    DocumentListItem,
    DocumentInfo,
    DocumentChunk,
    ErrorResponse,
)
from ..services.document_service import get_document_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    limit: int = 100,
    offset: int = 0,
    sort_by: str = "indexed_at",
    order: str = "desc"
):
    """
    Get list of all indexed documents.
    
    Returns document metadata including:
    - Filename and file type
    - Number of chunks and characters
    - Indexing timestamp
    
    Supports pagination and sorting.
    
    **Sort options:**
    - `indexed_at` - Sort by indexing date (default)
    - `file_name` - Sort alphabetically
    - `total_chunks` - Sort by chunk count
    - `total_characters` - Sort by content size
    
    **Order:**
    - `desc` - Descending (default)
    - `asc` - Ascending
    """
    try:
        # Validate parameters
        if limit < 1 or limit > 1000:
            raise HTTPException(
                status_code=400,
                detail="Limit must be between 1 and 1000"
            )
        
        if offset < 0:
            raise HTTPException(
                status_code=400,
                detail="Offset must be non-negative"
            )
        
        valid_sort_columns = ['indexed_at', 'file_name', 'total_chunks', 'total_characters']
        if sort_by not in valid_sort_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid sort_by. Must be one of: {', '.join(valid_sort_columns)}"
            )
        
        if order.lower() not in ['asc', 'desc']:
            raise HTTPException(
                status_code=400,
                detail="Order must be 'asc' or 'desc'"
            )
        
        # Get document service
        doc_service = get_document_service()
        
        # Fetch documents
        documents, total_documents, total_chunks, total_characters = await doc_service.get_documents(
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            order=order
        )
        
        logger.info(f"Retrieved {len(documents)} documents (offset: {offset}, limit: {limit})")
        
        return DocumentListResponse(
            documents=documents,
            total_documents=total_documents,
            total_chunks=total_chunks,
            total_characters=total_characters,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list documents: {str(e)}"
        )


@router.get("/{filename}", response_model=DocumentDetailResponse, responses={404: {"model": ErrorResponse}})
async def get_document(
    filename: str,
    include_chunks: bool = False
):
    """
    Get detailed information about a specific document.
    
    Returns:
    - Complete document metadata
    - Chunk statistics and indices
    - Quality metrics
    - Optionally: all document chunks with content
    
    **Parameters:**
    - `filename` - Document filename (URL encoded if contains special chars)
    - `include_chunks` - Include full chunk content (default: false)
    
    **Warning:** Setting `include_chunks=true` for large documents may result in large responses
    """
    try:
        if not filename or not filename.strip():
            raise HTTPException(
                status_code=400,
                detail="Filename cannot be empty"
            )
        
        # Get document service
        doc_service = get_document_service()
        
        # Fetch document
        result = await doc_service.get_document_by_filename(
            filename=filename,
            include_chunks=include_chunks
        )
        
        if result is None:
            logger.warning(f"Document not found: {filename}")
            raise HTTPException(
                status_code=404,
                detail=f"Document not found: {filename}"
            )
        
        document, chunks = result
        
        logger.info(f"Retrieved document: {filename} (chunks: {document.total_chunks})")
        
        return DocumentDetailResponse(
            document=document,
            chunks=chunks,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document {filename}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get document: {str(e)}"
        )


@router.get("/stats/overview", response_model=DocumentStatsResponse)
async def get_document_stats():
    """
    Get comprehensive document statistics.
    
    Returns detailed analytics including:
    - Total documents, chunks, and characters
    - Chunk distribution (min, max, average)
    - File type breakdown
    - Size distribution categories
    - Quality metrics
    
    Useful for monitoring index health and data distribution.
    """
    try:
        # Get document service
        doc_service = get_document_service()
        
        # Fetch statistics
        stats = await doc_service.get_document_stats()
        
        logger.info(f"Retrieved stats: {stats['total_documents']} documents")
        
        return DocumentStatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get statistics: {str(e)}"
        )


@router.post("/search", response_model=DocumentListResponse)
async def search_documents(request: DocumentSearchRequest):
    """
    Search documents by metadata criteria.
    
    **Search filters:**
    - `filename_pattern` - Filename pattern with wildcards (%, _)
    - `min_chunks` - Minimum number of chunks
    - `max_chunks` - Maximum number of chunks
    - `indexed_after` - Filter by indexing date
    - `limit` - Maximum results (1-1000)
    
    **Examples:**
    ```json
    {
      "filename_pattern": "report%",
      "min_chunks": 10,
      "limit": 50
    }
    ```
    
    Returns matching documents with metadata.
    """
    try:
        # Get document service
        doc_service = get_document_service()
        
        # Search documents
        documents, total_documents, total_chunks, total_characters = await doc_service.search_documents(
            filename_pattern=request.filename_pattern,
            min_chunks=request.min_chunks,
            max_chunks=request.max_chunks,
            indexed_after=request.indexed_after,
            limit=request.limit
        )
        
        logger.info(f"Search found {len(documents)} documents (pattern: {request.filename_pattern})")
        
        return DocumentListResponse(
            documents=documents,
            total_documents=total_documents,
            total_chunks=total_chunks,
            total_characters=total_characters,
        )
        
    except Exception as e:
        logger.error(f"Failed to search documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@router.delete("/{filename}", response_model=DeleteDocumentResponse, responses={404: {"model": ErrorResponse}})
async def delete_document(
    filename: str,
    delete_chunks: bool = True
):
    """
    Delete document from index.
    
    **⚠️ WARNING:** This permanently deletes the document from the vector database!
    
    **Process:**
    1. Checks if document exists
    2. Deletes document metadata
    3. Optionally removes all associated chunks and embeddings
    
    **Parameters:**
    - `filename` - Document filename to delete
    - `delete_chunks` - Also delete chunks (default: true, recommended)
    
    **Note:** This does NOT delete the source markdown file, only database records.
    
    Cannot be undone. Use with caution.
    """
    try:
        if not filename or not filename.strip():
            raise HTTPException(
                status_code=400,
                detail="Filename cannot be empty"
            )
        
        # Get document service
        doc_service = get_document_service()
        
        # Delete document
        success, chunks_deleted = await doc_service.delete_document(
            filename=filename,
            delete_chunks=delete_chunks
        )
        
        if not success:
            logger.warning(f"Document not found for deletion: {filename}")
            raise HTTPException(
                status_code=404,
                detail=f"Document not found: {filename}"
            )
        
        logger.info(f"Deleted document: {filename} ({chunks_deleted} chunks removed)")
        
        return DeleteDocumentResponse(
            success=True,
            filename=filename,
            chunks_deleted=chunks_deleted,
            message=f"Document '{filename}' deleted successfully ({chunks_deleted} chunks removed)",
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document {filename}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Delete failed: {str(e)}"
        )


@router.get("/{filename}/chunks", response_model=DocumentDetailResponse, responses={404: {"model": ErrorResponse}})
async def get_document_chunks(
    filename: str,
    limit: int = 100,
    offset: int = 0
):
    """
    Get chunks for a specific document with pagination.
    
    Returns:
    - Document metadata
    - Paginated list of chunks with content
    - Chunk indices and metadata
    
    **Pagination:**
    - `limit` - Chunks per page (1-1000, default: 100)
    - `offset` - Starting position (default: 0)
    
    Useful for reviewing document content and debugging chunking quality.
    """
    try:
        if not filename or not filename.strip():
            raise HTTPException(
                status_code=400,
                detail="Filename cannot be empty"
            )
        
        if limit < 1 or limit > 1000:
            raise HTTPException(
                status_code=400,
                detail="Limit must be between 1 and 1000"
            )
        
        if offset < 0:
            raise HTTPException(
                status_code=400,
                detail="Offset must be non-negative"
            )
        
        # Get document service
        doc_service = get_document_service()
        
        # Fetch chunks
        result = await doc_service.get_document_chunks(
            filename=filename,
            limit=limit,
            offset=offset
        )
        
        if result is None:
            logger.warning(f"Document not found: {filename}")
            raise HTTPException(
                status_code=404,
                detail=f"Document not found: {filename}"
            )
        
        document_info, chunks = result
        
        logger.info(f"Retrieved {len(chunks)} chunks for {filename} (offset: {offset})")
        
        return DocumentDetailResponse(
            document=document_info,
            chunks=chunks,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chunks for {filename}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get chunks: {str(e)}"
        )


@router.post("/upload", response_model=dict)
async def upload_document(
    file: UploadFile = File(...),
    auto_index: bool = Form(False)
):
    """
    Upload a document file to Supabase Storage for processing.

    **Process:**
    1. Validates file type (supports all Docling formats)
    2. Uploads to Supabase Storage (bucket: vehicle-documents, folder: raw/pending/)
    3. Creates entry in document_registry
    4. File is ready for conversion and indexing

    **Supported formats:**
    - Documents: PDF, DOCX, DOC, PPTX, PPT
    - Text: TXT, HTML, HTM
    - Images: PNG, JPG, JPEG, TIFF (with OCR)

    **Parameters:**
    - `file` - Document file to upload
    - `auto_index` - Not used (kept for API compatibility)

    **Workflow:**
    1. Upload files here → Supabase Storage
    2. Start conversion (Docling downloads from Storage)
    3. Start indexing (chunking + embeddings)

    **Example:**
    ```bash
    curl -X POST "http://localhost:8000/api/documents/upload" \\
         -F "file=@document.docx"
    ```

    Returns upload confirmation with file details.
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="No filename provided"
            )

        # Get file extension
        file_ext = Path(file.filename).suffix.lower()

        # Supported formats (same as Docling)
        ALLOWED_EXTENSIONS = {
            '.pdf', '.docx', '.doc', '.pptx', '.ppt',
            '.txt', '.html', '.htm',
            '.png', '.jpg', '.jpeg', '.tiff'
        }

        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_ext}. Supported formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )

        # Read file content
        content = await file.read()

        if not content:
            raise HTTPException(
                status_code=400,
                detail="File is empty"
            )

        file_size = len(content)

        # Import Storage components
        import sys
        import os
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent.parent.parent
        sys.path.insert(0, str(project_root / "rag_indexer"))

        from storage.storage_manager import SupabaseStorageManager
        from chunking_vectors.registry_manager import DocumentRegistryManager

        # Get connection string from environment
        connection_string = os.getenv('SUPABASE_CONNECTION_STRING')
        if not connection_string:
            raise HTTPException(
                status_code=500,
                detail="SUPABASE_CONNECTION_STRING not configured"
            )

        # Initialize managers
        storage_manager = SupabaseStorageManager()
        registry_manager = DocumentRegistryManager(connection_string=connection_string)

        # Upload to Supabase Storage
        logger.info(f"Uploading {file.filename} ({file_size} bytes) to Supabase Storage...")

        upload_result = storage_manager.upload_document(
            file=content,  # bytes content
            original_filename=file.filename,
            document_type=None,  # Will be detected later
            target_folder='raw/pending'
        )

        logger.info(f"✅ Uploaded to Storage: {upload_result['storage_path']}")

        # Create registry entry
        registry_id = registry_manager.create_entry_from_storage(
            storage_path=upload_result['storage_path'],
            original_filename=file.filename,
            file_size=file_size,
            content_type=file.content_type or 'application/octet-stream',
            storage_bucket='vehicle-documents',
            document_type=None,
            vehicle_id=None,
            extracted_data=None
        )

        if registry_id:
            logger.info(f"✅ Created registry entry: {registry_id}")
        else:
            logger.warning(f"⚠️ Failed to create registry entry for {file.filename}")

        return {
            "success": True,
            "message": f"File uploaded successfully to Supabase Storage: {file.filename}",
            "filename": file.filename,
            "file_size": file_size,
            "file_type": file_ext,
            "storage_path": upload_result['storage_path'],
            "storage_bucket": "vehicle-documents",
            "registry_id": str(registry_id) if registry_id else None,
            "storage_status": "pending",
            "next_steps": [
                "1. File is now in Supabase Storage (raw/pending/)",
                "2. Start conversion to process from Storage",
                "3. Start indexing to create embeddings",
                "4. File will appear in documents list"
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload document: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )


@router.get("/missing/files", response_model=MissingDocumentsResponse)
async def get_missing_documents():
    """
    Get files present in markdown directory but missing from database.
    
    **Analysis:**
    - Scans markdown directory for .md files
    - Compares with database records
    - Identifies files that should be indexed but aren't
    
    **Returns:**
    - List of missing files
    - Counts and success rate
    - Comparison statistics
    
    **Use cases:**
    - Detecting indexing failures
    - Finding documents that need re-indexing
    - Verifying index completeness
    
    **Troubleshooting:** If many files are missing, consider running full reindex.
    """
    try:
        # Get document service
        doc_service = get_document_service()
        
        # Analyze missing documents
        (missing_files, total_missing, total_in_directory, 
         total_in_database, success_rate) = await doc_service.get_missing_documents()
        
        logger.info(f"Missing documents analysis: {total_missing}/{total_in_directory} missing")
        
        return MissingDocumentsResponse(
            missing_files=missing_files,
            total_missing=total_missing,
            total_in_directory=total_in_directory,
            total_in_database=total_in_database,
            success_rate=success_rate,
        )
        
    except Exception as e:
        logger.error(f"Failed to get missing documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )