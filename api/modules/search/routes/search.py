# api/modules/search/routes/search.py
# Simplified search endpoint - delegates all logic to backend services

import logging
import time
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List

from api.modules.search.models.schemas import SearchRequest, SearchResponse, SearchResult, ErrorResponse
from api.core.dependencies import get_system_components, SystemComponents

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    system_components: SystemComponents = Depends(get_system_components)
):
    """
    Simplified search endpoint

    Delegates all business logic to backend services:
    - Multi-strategy retrieval (vector + database)
    - Hybrid results fusion and ranking
    - Quality filtering

    API layer only handles:
    - Request validation (via Pydantic)
    - Routing to backend
    - Response formatting
    - Error handling
    """

    start_time = time.time()

    try:
        logger.info("=" * 80)
        logger.info(f"SEARCH REQUEST: {request.query}")
        logger.info("=" * 80)

        # ====================================================================
        # STAGE 1: Multi-Strategy Retrieval (Backend)
        # ====================================================================
        logger.info("STAGE 1: Multi-Strategy Retrieval")
        retrieval_start = time.time()

        components = system_components.get_components()

        multi_retrieval_result = await components["retriever"].multi_retrieve(
            queries=[request.query],
            extracted_entity=None,
            required_terms=None
        )

        retrieval_time = time.time() - retrieval_start
        logger.info(f"✓ Retrieved {len(multi_retrieval_result.results)} candidates")
        logger.info(f"  Methods: {', '.join(multi_retrieval_result.methods_used)}")
        logger.info(f"  Time: {retrieval_time:.3f}s")

        # ====================================================================
        # STAGE 2: Hybrid Results Fusion + LLM Re-ranking (Backend)
        # ====================================================================
        logger.info("STAGE 2: Hybrid Results Fusion + LLM Re-ranking")
        fusion_start = time.time()

        # Use ASYNC version for full LLM re-ranking support
        fusion_result = await components["fusion_engine"].fuse_results_async(
            all_results=multi_retrieval_result.results,
            original_query=request.query,
            extracted_entity=None,  # Backend will handle entity extraction if needed
            required_terms=None
        )

        fusion_time = time.time() - fusion_start
        logger.info(f"✓ Fused to {fusion_result.final_count} documents")
        logger.info(f"  Fusion method: {fusion_result.fusion_method}")
        logger.info(f"  Time: {fusion_time:.3f}s")

        if fusion_result.fused_results:
            top_scores = [f"{doc.similarity_score:.3f}" for doc in fusion_result.fused_results[:3]]
            logger.info(f"  Top scores: {top_scores}")

        # ====================================================================
        # STAGE 3: Format Response
        # ====================================================================
        logger.info("STAGE 3: Format Response")

        # Convert backend results to API response format
        # Apply top_k limit (default 10 if not specified)
        top_k = request.top_k or 10
        search_results = []
        for result in fusion_result.fused_results[:top_k]:
            # Extract metadata for frontend compatibility
            metadata_dict = {
                "match_type": result.metadata.get("match_type", "unknown"),
                "hybrid_weighted_score": result.metadata.get("hybrid_weighted_score", result.similarity_score),
                "fusion_method": result.metadata.get("fusion_method", "unknown"),
                "database_strategy": result.metadata.get("database_strategy"),
                **result.metadata
            }

            search_results.append(SearchResult(
                content=result.content,
                file_name=result.filename,
                score=result.similarity_score,
                # Frontend compatibility fields (top-level)
                source_method=result.source_method,
                filename=result.filename,
                similarity_score=result.similarity_score,
                chunk_index=result.chunk_index if hasattr(result, 'chunk_index') else 0,
                # Additional metadata
                metadata=metadata_dict
            ))

        total_time = time.time() - start_time

        logger.info("=" * 80)
        logger.info("SEARCH COMPLETED")
        logger.info(f"Total Time: {total_time:.3f}s | Results: {len(search_results)}")
        logger.info(f"Breakdown: Retrieval={retrieval_time:.3f}s | Fusion={fusion_time:.3f}s")
        logger.info("=" * 80)

        return SearchResponse(
            success=True,
            query=request.query,
            results=search_results,
            total_results=len(search_results),
            search_time=total_time,
            metadata={
                "retrieval_methods": multi_retrieval_result.methods_used,
                "fusion_method": fusion_result.fusion_method,
                "retrieval_time": retrieval_time,
                "fusion_time": fusion_time,
                "original_candidates": len(multi_retrieval_result.results),
                "after_fusion": fusion_result.final_count
            }
        )

    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/health", tags=["Search"])
async def search_health(
    system_components: SystemComponents = Depends(get_system_components)
):
    """
    Health check for search system
    """
    try:
        components = system_components.get_components()

        # Check if retriever is available
        retriever_available = components.get("retriever") is not None
        fusion_available = components.get("fusion_engine") is not None

        return {
            "status": "healthy" if (retriever_available and fusion_available) else "degraded",
            "components": {
                "retriever": "available" if retriever_available else "unavailable",
                "fusion_engine": "available" if fusion_available else "unavailable"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
