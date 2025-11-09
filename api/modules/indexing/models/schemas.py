# api/modules/indexing/models/schemas.py
# Pydantic models for indexing API request/response validation

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Any, Literal
from datetime import datetime
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class IndexingMode(str, Enum):
    """Indexing mode"""
    FULL = "full"           # Full reindex
    INCREMENTAL = "incremental"  # Only new/modified files


class IndexingStatus(str, Enum):
    """Indexing process status"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ConversionStatus(str, Enum):
    """Conversion process status"""
    PENDING = "pending"
    CONVERTING = "converting"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingStage(str, Enum):
    """Processing pipeline stage"""
    CONVERSION = "conversion"
    LOADING = "loading"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    SAVING = "saving"
    COMPLETED = "completed"


# ============================================================================
# REQUEST MODELS
# ============================================================================

class IndexingRequest(BaseModel):
    """Request to start indexing process"""
    mode: IndexingMode = Field(
        default=IndexingMode.INCREMENTAL,
        description="Indexing mode: full or incremental"
    )
    documents_dir: Optional[str] = Field(
        default=None,
        description="Custom documents directory (overrides config)"
    )
    skip_conversion: bool = Field(
        default=False,
        description="Skip document conversion (Part 1)"
    )
    skip_indexing: bool = Field(
        default=False,
        description="Skip vector indexing (Part 2)"
    )
    batch_size: Optional[int] = Field(
        default=None,
        ge=1,
        le=200,
        description="Processing batch size"
    )
    force_reindex: bool = Field(
        default=False,
        description="Force reindex even if files haven't changed"
    )
    delete_existing: bool = Field(
        default=False,
        description="Delete existing records before indexing"
    )
    
    @validator('documents_dir')
    def validate_documents_dir(cls, v):
        if v is not None and len(v.strip()) == 0:
            raise ValueError("documents_dir cannot be empty string")
        return v


class ConversionRequest(BaseModel):
    """Request to start document conversion"""
    input_dir: Optional[str] = Field(
        default=None,
        description="Input directory with raw documents"
    )
    output_dir: Optional[str] = Field(
        default=None,
        description="Output directory for markdown files"
    )
    incremental: bool = Field(
        default=True,
        description="Skip already converted files"
    )
    formats: Optional[List[str]] = Field(
        default=None,
        description="Specific formats to convert (e.g., ['pdf', 'docx'])"
    )
    enable_ocr: Optional[bool] = Field(
        default=None,
        description="Enable OCR for image-based documents"
    )
    max_file_size_mb: Optional[int] = Field(
        default=None,
        ge=1,
        le=500,
        description="Maximum file size in MB"
    )


class ReindexFilesRequest(BaseModel):
    """Request to reindex specific files"""
    filenames: List[str] = Field(
        ...,
        min_items=1,
        description="List of filenames to reindex"
    )
    force: bool = Field(
        default=False,
        description="Force reindex even if files haven't changed"
    )


class DeleteDocumentRequest(BaseModel):
    """Request to delete document from index"""
    filename: str = Field(
        ...,
        min_length=1,
        description="Filename to delete"
    )
    delete_chunks: bool = Field(
        default=True,
        description="Also delete associated chunks"
    )


class DocumentUploadRequest(BaseModel):
    """Request metadata for document upload"""
    filename: str = Field(..., description="Original filename")
    file_type: str = Field(..., description="File type/extension")
    file_size: int = Field(..., ge=0, description="File size in bytes")
    auto_index: bool = Field(
        default=True,
        description="Automatically index after upload"
    )


class DocumentSearchRequest(BaseModel):
    """Request to search documents by metadata"""
    filename_pattern: Optional[str] = Field(
        default=None,
        description="Filename pattern (supports wildcards)"
    )
    min_chunks: Optional[int] = Field(
        default=None,
        ge=0,
        description="Minimum number of chunks"
    )
    max_chunks: Optional[int] = Field(
        default=None,
        ge=0,
        description="Maximum number of chunks"
    )
    indexed_after: Optional[datetime] = Field(
        default=None,
        description="Filter by indexed date"
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum results to return"
    )


# ============================================================================
# RESPONSE MODELS - INDEXING
# ============================================================================

class IndexingProgress(BaseModel):
    """Current indexing progress"""
    status: IndexingStatus
    stage: Optional[ProcessingStage] = None
    current_stage_name: str = ""
    progress_percentage: float = Field(ge=0, le=100)
    
    # File processing
    total_files: int = 0
    processed_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0  # <--- Поле добавлено здесь
    

    registry_entries_created: int = 0  # Number of registry entries created/updated
    # Chunk processing
    total_chunks: int = 0
    processed_chunks: int = 0
    
    # Time tracking
    start_time: Optional[datetime] = None
    elapsed_time: float = 0.0  # seconds
    estimated_remaining: Optional[float] = None  # seconds
    
    # Current operation
    current_file: Optional[str] = None
    current_batch: Optional[int] = None
    total_batches: Optional[int] = None
    
    # Performance metrics
    processing_speed: float = 0.0  # chunks/second
    avg_time_per_file: float = 0.0  # seconds


class IndexingStatistics(BaseModel):
    """Statistics from indexing process"""
    # Document stats
    documents_loaded: int = 0
    documents_converted: int = 0
    documents_indexed: int = 0
    documents_processed: int = 0  # Alias for documents_indexed (for frontend compatibility)
    skipped_files: int = 0 # <--- Поле добавлено здесь
    
    # Chunk stats
    chunks_created: int = 0
    chunks_valid: int = 0
    chunks_invalid: int = 0
    chunks_saved: int = 0
    
    # Quality metrics
    success_rate: float = 0.0
    filter_success_rate: float = 0.0
    avg_chunk_length: float = 0.0
    
    # Performance metrics
    total_time: float = 0.0
    conversion_time: float = 0.0
    chunking_time: float = 0.0
    embedding_time: float = 0.0
    saving_time: float = 0.0
    
    # API usage (Gemini)
    gemini_api_calls: int = 0
    gemini_tokens_used: int = 0
    gemini_rate_limit_hits: int = 0


class IndexingResponse(BaseModel):
    """Response after starting indexing"""
    success: bool
    message: str
    task_id: str
    mode: IndexingMode
    estimated_duration: Optional[float] = None  # seconds
    files_to_process: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)


class IndexingStatusResponse(BaseModel):
    """Response for indexing status check"""
    task_id: str
    progress: IndexingProgress
    statistics: Optional[IndexingStatistics] = None # Сделаем опциональным
    errors: List[str] = []
    warnings: List[str] = []
    timestamp: datetime = Field(default_factory=datetime.now)


class IndexingHistoryItem(BaseModel):
    """Single indexing history record"""
    task_id: str
    mode: IndexingMode
    status: IndexingStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None  # seconds
    files_processed: int = 0
    chunks_created: int = 0
    success_rate: float = 0.0
    error_message: Optional[str] = None


class IndexingHistoryResponse(BaseModel):
    """Response with indexing history"""
    history: List[IndexingHistoryItem]
    total_runs: int
    last_successful_run: Optional[datetime] = None
    last_failed_run: Optional[datetime] = None
    timestamp: datetime = Field(default_factory=datetime.now)


# ============================================================================
# RESPONSE MODELS - CONVERSION
# ============================================================================

class ConversionProgress(BaseModel):
    """Document conversion progress"""
    status: ConversionStatus
    total_files: int = 0
    converted_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0
    progress_percentage: float = Field(ge=0, le=100)
    current_file: Optional[str] = None
    elapsed_time: float = 0.0
    estimated_remaining: Optional[float] = None


class ConversionResult(BaseModel):
    """Result of document conversion"""
    filename: str
    status: ConversionStatus
    input_path: str
    output_path: Optional[str] = None
    file_size: int = 0
    conversion_time: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = {}


class ConversionResponse(BaseModel):
    """Response after starting conversion"""
    success: bool
    message: str
    task_id: str
    files_to_convert: int = 0
    supported_formats: List[str] = []
    timestamp: datetime = Field(default_factory=datetime.now)


class ConversionStatusResponse(BaseModel):
    """Response for conversion status check"""
    task_id: str
    progress: ConversionProgress
    results: List[ConversionResult] = []
    errors: List[str] = []
    timestamp: datetime = Field(default_factory=datetime.now)


class SupportedFormatsResponse(BaseModel):
    """Response with supported document formats"""
    formats: List[str]
    ocr_enabled: bool
    max_file_size_mb: int
    timestamp: datetime = Field(default_factory=datetime.now)


# ============================================================================
# RESPONSE MODELS - DOCUMENTS
# ============================================================================

class DocumentChunk(BaseModel):
    """Single document chunk information"""
    chunk_index: int
    content: str
    content_length: int
    metadata: Dict[str, Any] = {}


class DocumentInfo(BaseModel):
    """Detailed document information"""
    filename: str
    file_path: Optional[str] = None
    file_type: str = ""
    
    # Chunk info
    total_chunks: int = 0
    chunk_indices: List[int] = []
    
    # Content stats
    total_characters: int = 0
    avg_chunk_length: float = 0.0
    
    # Indexing info
    indexed_at: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    
    # Quality metrics
    embedding_quality: Optional[float] = None
    
    # Metadata
    metadata: Dict[str, Any] = {}


class DocumentListItem(BaseModel):
    """Document item in list"""
    filename: str
    total_chunks: int
    total_characters: int
    indexed_at: Optional[datetime] = None
    file_type: str = ""


class DocumentListResponse(BaseModel):
    """Response with list of documents"""
    documents: List[DocumentListItem]
    total_documents: int
    total_chunks: int
    total_characters: int
    timestamp: datetime = Field(default_factory=datetime.now)


class DocumentDetailResponse(BaseModel):
    """Response with detailed document information"""
    document: DocumentInfo
    chunks: Optional[List[DocumentChunk]] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class DocumentStatsResponse(BaseModel):
    """Response with document statistics"""
    total_documents: int
    total_chunks: int
    total_characters: int
    
    # Distribution stats
    avg_chunks_per_document: float
    min_chunks: int
    max_chunks: int
    
    # File type distribution
    file_types: Dict[str, int] = {}
    
    # Size distribution
    size_distribution: Dict[str, int] = {
        "small": 0,      # < 1000 chars
        "medium": 0,     # 1000-5000 chars
        "large": 0,      # 5000-20000 chars
        "very_large": 0  # > 20000 chars
    }
    
    # Quality metrics
    avg_embedding_quality: Optional[float] = None
    
    timestamp: datetime = Field(default_factory=datetime.now)


class DeleteDocumentResponse(BaseModel):
    """Response after deleting document"""
    success: bool
    filename: str
    chunks_deleted: int
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)


class MissingDocumentsResponse(BaseModel):
    """Response with documents missing from database"""
    missing_files: List[str]
    total_missing: int
    total_in_directory: int
    total_in_database: int
    success_rate: float
    timestamp: datetime = Field(default_factory=datetime.now)


# ============================================================================
# RESPONSE MODELS - MONITORING
# ============================================================================

class PipelineStageMetrics(BaseModel):
    """Metrics for a single pipeline stage"""
    stage_name: str
    status: str
    progress_percentage: float = Field(ge=0, le=100)
    items_processed: int = 0
    items_total: int = 0
    elapsed_time: float = 0.0
    estimated_remaining: Optional[float] = None
    errors: int = 0


class PipelineStatusResponse(BaseModel):
    """Response with pipeline status"""
    overall_status: IndexingStatus
    current_stage: Optional[ProcessingStage] = None
    stages: List[PipelineStageMetrics] = []
    overall_progress: float = Field(ge=0, le=100)
    timestamp: datetime = Field(default_factory=datetime.now)


class PerformanceMetricsResponse(BaseModel):
    """Response with performance metrics"""
    # Processing speed
    current_speed: float = 0.0  # chunks/second
    average_speed: float = 0.0  # chunks/second
    peak_speed: float = 0.0     # chunks/second
    
    # Time metrics
    total_processing_time: float = 0.0
    avg_time_per_file: float = 0.0
    avg_time_per_chunk: float = 0.0
    
    # Resource usage
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    
    # API metrics (Gemini)
    api_calls: int = 0
    api_calls_per_minute: float = 0.0
    api_errors: int = 0
    api_rate_limit_hits: int = 0
    
    # Efficiency
    processing_efficiency: float = 0.0  # successful / total
    
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorLogItem(BaseModel):
    """Single error log entry"""
    timestamp: datetime
    error_type: str
    error_message: str
    file_name: Optional[str] = None
    stage: Optional[ProcessingStage] = None
    details: Dict[str, Any] = {}


class ErrorLogResponse(BaseModel):
    """Response with error logs"""
    errors: List[ErrorLogItem]
    total_errors: int
    error_types: Dict[str, int] = {}
    most_recent_error: Optional[datetime] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class ProcessingQueueItem(BaseModel):
    """Item in processing queue"""
    filename: str
    position: int
    status: str
    estimated_start_time: Optional[datetime] = None


class ProcessingQueueResponse(BaseModel):
    """Response with processing queue"""
    queue: List[ProcessingQueueItem]
    queue_length: int
    processing_now: Optional[str] = None
    estimated_completion: Optional[datetime] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class ChunkAnalysisResponse(BaseModel):
    """Response with chunk analysis"""
    # Overall stats
    total_chunks: int
    total_files: int
    avg_chunks_per_file: float
    
    # Chunk size distribution
    min_chunk_size: int
    max_chunk_size: int
    avg_chunk_size: float
    median_chunk_size: int
    
    # Top files by chunks
    top_files: List[Dict[str, Any]] = []
    
    # Quality distribution
    quality_distribution: Dict[str, int] = {
        "excellent": 0,  # > 1000 chars
        "good": 0,       # 500-1000 chars
        "moderate": 0,   # 200-500 chars
        "poor": 0        # < 200 chars
    }
    
    timestamp: datetime = Field(default_factory=datetime.now)


class DatabaseStatsResponse(BaseModel):
    """Response with database statistics"""
    # Table stats
    total_records: int
    table_size_mb: float
    index_size_mb: float
    
    # Vector stats
    vector_dimension: int
    total_vectors: int
    
    # Performance
    avg_query_time_ms: Optional[float] = None
    
    # Health
    connection_status: str
    last_backup: Optional[datetime] = None
    
    timestamp: datetime = Field(default_factory=datetime.now)


# ============================================================================
# GENERIC RESPONSES
# ============================================================================

class SuccessResponse(BaseModel):
    """Generic success response"""
    success: bool = True
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorResponse(BaseModel):
    """Generic error response"""
    success: bool = False
    error: str
    error_type: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class ValidationErrorResponse(BaseModel):
    """Validation error response"""
    success: bool = False
    error: str = "Validation error"
    validation_errors: List[Dict[str, Any]]
    timestamp: datetime = Field(default_factory=datetime.now)