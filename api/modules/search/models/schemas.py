# api/models/schemas.py
# Simplified Pydantic models for API request/response validation

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime


class SearchRequest(BaseModel):
    """Simplified request model for search endpoint"""
    query: str = Field(..., min_length=1, max_length=1000, description="Search query text")
    top_k: Optional[int] = Field(default=10, ge=1, le=50, description="Maximum number of results to return")
    similarity_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Minimum similarity threshold")


class SearchResult(BaseModel):
    """Single search result from backend"""
    content: str = Field(..., description="Document content preview")
    file_name: str = Field(..., description="Source document filename")
    score: float = Field(..., description="Similarity/relevance score")

    # Frontend compatibility fields (top-level for direct access)
    source_method: str = Field(..., description="Search method used (database_hybrid, vector_smart_threshold)")
    filename: str = Field(..., description="Filename (duplicate for frontend compatibility)")
    similarity_score: float = Field(..., description="Similarity score (duplicate for frontend compatibility)")
    chunk_index: int = Field(default=0, description="Chunk index in document")

    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional result metadata")


class SearchResponse(BaseModel):
    """Simplified response model for search endpoint"""
    success: bool = Field(default=True)
    query: str = Field(..., description="Original search query")
    results: List[SearchResult] = Field(default_factory=list, description="Search results")
    total_results: int = Field(..., description="Total number of results returned")
    search_time: float = Field(..., description="Total search time in seconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Search metadata (methods used, timing breakdown)")
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = False
    error: str
    error_type: str
    timestamp: datetime = Field(default_factory=datetime.now)


class SystemStatus(BaseModel):
    """System status response"""
    status: str
    components: Dict[str, Any]
    database: Dict[str, Any]
    embedding: Dict[str, Any]
    hybrid_enabled: bool
    timestamp: datetime = Field(default_factory=datetime.now)


class HealthCheck(BaseModel):
    """Health check response"""
    status: str
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.now)