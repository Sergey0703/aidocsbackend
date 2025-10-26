# api/modules/search/routes/search.py
# Simplified search endpoint - delegates all logic to backend services
# UPDATED: Added query preprocessing to filter stop words

import logging
import time
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List

from api.modules.search.models.schemas import SearchRequest, SearchResponse, SearchResult, ErrorResponse
from api.core.dependencies import get_system_components, SystemComponents
from query_processing.query_preprocessor import QueryPreprocessor

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize query preprocessor (will be created per request with config)
_query_preprocessor = None


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

        components = system_components.get_components()

        # ====================================================================
        # STAGE 0: Query Preprocessing (NEW!)
        # ====================================================================
        logger.info("STAGE 0: Query Preprocessing")
        preprocess_start = time.time()

        # Initialize preprocessor with config
        global _query_preprocessor
        if _query_preprocessor is None:
            _query_preprocessor = QueryPreprocessor(
                components["config"],
                enable_ai_enhancement=True  # Enable AI for complex queries
            )

        # Preprocess query
        preprocessing_result = _query_preprocessor.preprocess(request.query)

        preprocess_time = time.time() - preprocess_start

        # Check if query was rejected
        if not preprocessing_result.is_valid:
            logger.warning(f"[!] Query rejected: {preprocessing_result.rejection_reason}")
            logger.info(f"  Removed stop words: {preprocessing_result.removed_stop_words}")
            logger.info(f"  Time: {preprocess_time:.3f}s")

            # Return user-friendly error message as string for frontend compatibility
            error_message = preprocessing_result.rejection_reason
            if preprocessing_result.removed_stop_words:
                removed = ", ".join(preprocessing_result.removed_stop_words)
                error_message += f" (removed: {removed})"

            raise HTTPException(
                status_code=400,
                detail=error_message
            )

        # Log preprocessing result
        logger.info(f"[+] Query preprocessed: '{request.query}' -> '{preprocessing_result.query}'")
        logger.info(f"  Method: {preprocessing_result.method}")
        if preprocessing_result.removed_stop_words:
            logger.info(f"  Removed stop words: {preprocessing_result.removed_stop_words}")
        if preprocessing_result.ai_enhancement:
            logger.info(f"  AI enhancement: {preprocessing_result.ai_enhancement}")
        logger.info(f"  Time: {preprocess_time:.3f}s")

        # Use preprocessed query for search
        search_query = preprocessing_result.query

        # ====================================================================
        # STAGE 1: Multi-Strategy Retrieval (Backend)
        # ====================================================================
        logger.info("STAGE 1: Multi-Strategy Retrieval")
        retrieval_start = time.time()

        multi_retrieval_result = await components["retriever"].multi_retrieve(
            queries=[search_query],  # Use preprocessed query!
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
            original_query=search_query,  # Use preprocessed query!
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
        # STAGE 3: Answer Generation (NEW!)
        # ====================================================================
        logger.info("STAGE 3: Answer Generation")
        answer_start = time.time()

        generated_answer = None
        if fusion_result.fused_results:
            # Use QueryEngine to generate natural language answer
            try:
                answer_result = await components["answer_engine"].generate_answer(
                    query=search_query,
                    retrieved_results=fusion_result.fused_results,
                    original_query=request.query
                )
                generated_answer = answer_result.answer
                answer_time = time.time() - answer_start
                logger.info(f"✓ Answer generated (confidence: {answer_result.confidence:.3f})")
                logger.info(f"  Time: {answer_time:.3f}s")
                logger.info(f"  Preview: {generated_answer[:100]}...")
            except Exception as e:
                answer_time = time.time() - answer_start
                logger.warning(f"[!] Answer generation failed: {e}")
                logger.info(f"  Time: {answer_time:.3f}s")
                # Continue without answer - still return search results
        else:
            answer_time = 0
            logger.info("  No results to generate answer from")

        # ====================================================================
        # STAGE 4: Format Response
        # ====================================================================
        logger.info("STAGE 4: Format Response")

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

            # IMPROVED SCORE CALCULATION:
            # Prioritize LLM relevance score (0-10 scale) over base similarity_score
            # Convert to 0-1 scale for consistency
            display_score = result.similarity_score  # Default fallback

            if 'llm_relevance_score' in result.metadata:
                # LLM score is 0-10, convert to 0-1
                llm_score = result.metadata['llm_relevance_score']
                display_score = llm_score / 10.0
                logger.debug(f"[*] Using LLM score for {result.filename}: {llm_score}/10 = {display_score:.3f}")
            elif result.metadata.get("match_type") == "exact_match":
                # Exact matches should show high confidence
                display_score = 0.95
            elif result.metadata.get("match_type") == "strong_match":
                # Strong matches show high confidence
                display_score = 0.85

            # Ensure score is in valid range
            display_score = max(0.0, min(1.0, display_score))

            search_results.append(SearchResult(
                content=result.content,
                file_name=result.filename,
                score=display_score,
                # Frontend compatibility fields (top-level)
                source_method=result.source_method,
                filename=result.filename,
                similarity_score=display_score,
                chunk_index=result.chunk_index if hasattr(result, 'chunk_index') else 0,
                # Additional metadata
                metadata=metadata_dict
            ))

        total_time = time.time() - start_time

        logger.info("=" * 80)
        logger.info("SEARCH COMPLETED")
        logger.info(f"Total Time: {total_time:.3f}s | Results: {len(search_results)}")
        logger.info(f"Breakdown: Retrieval={retrieval_time:.3f}s | Fusion={fusion_time:.3f}s | Answer={answer_time:.3f}s")
        if generated_answer:
            logger.info(f"Answer: {generated_answer[:150]}...")
        logger.info("=" * 80)

        return SearchResponse(
            success=True,
            query=request.query,
            answer=generated_answer,  # NEW: Natural language answer!
            results=search_results,
            total_results=len(search_results),
            search_time=total_time,
            metadata={
                "retrieval_methods": multi_retrieval_result.methods_used,
                "fusion_method": fusion_result.fusion_method,
                "retrieval_time": retrieval_time,
                "fusion_time": fusion_time,
                "answer_time": answer_time,  # NEW: Answer generation time
                "has_answer": generated_answer is not None,  # NEW: Whether answer was generated
                "original_candidates": len(multi_retrieval_result.results),
                "after_fusion": fusion_result.final_count
            }
        )

    except HTTPException:
        # Re-raise HTTPException (e.g., from query validation)
        raise
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
