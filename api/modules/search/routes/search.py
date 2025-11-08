# api/modules/search/routes/search.py
# Simplified search endpoint - delegates all logic to backend services
# UPDATED: Added query preprocessing to filter stop words
# UPDATED: Added comprehensive error handling and validation

import logging
import time
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List

from api.modules.search.models.schemas import (
    SearchRequest, SearchResponse, SearchResult, ErrorResponse,
    EntityResult, RewriteResult, PerformanceMetrics, PipelineEfficiency
)
from api.core.dependencies import get_system_components, SystemComponents
from api.core.validators import QueryValidator, ErrorMessageFormatter
from rag_client.query_processing.query_preprocessor import QueryPreprocessor

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize query preprocessor (will be created per request with config)
_query_preprocessor = None

# Timeout settings (seconds)
SEARCH_TIMEOUT = 60  # Maximum time for entire search operation
RETRIEVAL_TIMEOUT = 30  # Maximum time for retrieval stage
FUSION_TIMEOUT = 20  # Maximum time for fusion stage
ANSWER_TIMEOUT = 15  # Maximum time for answer generation


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
        # ====================================================================
        # VALIDATION: Input validation and sanitization
        # ====================================================================

        # Validate query
        is_valid, sanitized_query, error_msg = QueryValidator.validate_query(request.query)
        if not is_valid:
            logger.warning(f"Invalid query rejected: {request.query} - {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)

        # Use sanitized query
        request.query = sanitized_query

        # Validate top_k
        if request.top_k:
            is_valid, sanitized_top_k, error_msg = QueryValidator.validate_top_k(request.top_k)
            if not is_valid:
                logger.warning(f"Invalid top_k: {request.top_k} - {error_msg}")
                request.top_k = sanitized_top_k  # Use corrected value

        # Validate similarity_threshold
        if request.similarity_threshold:
            is_valid, sanitized_threshold, error_msg = QueryValidator.validate_similarity_threshold(
                request.similarity_threshold
            )
            if not is_valid:
                logger.warning(f"Invalid similarity_threshold: {request.similarity_threshold} - {error_msg}")
                request.similarity_threshold = sanitized_threshold  # Use corrected value

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
        # STAGE 0.5: Entity Extraction (NEW!)
        # ====================================================================
        logger.info("STAGE 0.5: Entity Extraction")
        extraction_start = time.time()

        entity_result_data = await components["entity_extractor"].extract_entity(search_query)
        extraction_time = time.time() - extraction_start

        logger.info(f"✓ Entity: '{entity_result_data.entity}' | Method: {entity_result_data.method} | Confidence: {entity_result_data.confidence:.2%} | Time: {extraction_time:.3f}s")

        # ====================================================================
        # STAGE 0.6: Query Rewriting (NEW!)
        # ====================================================================
        logger.info("STAGE 0.6: Query Rewriting")
        rewrite_start = time.time()

        rewrite_result_data = await components["query_rewriter"].rewrite_query(
            search_query, entity_result_data.entity
        )
        rewrite_time = time.time() - rewrite_start

        logger.info(f"✓ Query rewrites: {len(rewrite_result_data.rewrites)} variants | Method: {rewrite_result_data.method} | Time: {rewrite_time:.3f}s")

        # Build queries list for retrieval (original + rewrites)
        retrieval_queries = [search_query] + rewrite_result_data.rewrites[:2]  # Original + top 2 rewrites

        # Get required terms for content filtering
        required_terms = []
        if entity_result_data.entity != search_query.strip():
            entity_words = [word.lower() for word in entity_result_data.entity.split() if len(word) > 2]
            required_terms = entity_words

        # ====================================================================
        # STAGE 1: Multi-Strategy Retrieval (Backend) with Timeout
        # ====================================================================
        logger.info("STAGE 1: Multi-Strategy Retrieval")
        retrieval_start = time.time()

        try:
            multi_retrieval_result = await asyncio.wait_for(
                components["retriever"].multi_retrieve(
                    queries=retrieval_queries,  # Use original + rewrites!
                    extracted_entity=entity_result_data.entity,
                    required_terms=required_terms
                ),
                timeout=RETRIEVAL_TIMEOUT
            )
        except asyncio.TimeoutError:
            retrieval_time = time.time() - retrieval_start
            logger.error(f"Retrieval stage timeout after {retrieval_time:.3f}s")
            raise HTTPException(
                status_code=504,
                detail=f"Search retrieval timed out after {retrieval_time:.1f} seconds. The query may be too complex. Please try a simpler search."
            )

        retrieval_time = time.time() - retrieval_start
        logger.info(f"✓ Retrieved {len(multi_retrieval_result.results)} candidates")
        logger.info(f"  Methods: {', '.join(multi_retrieval_result.methods_used)}")
        logger.info(f"  Time: {retrieval_time:.3f}s")

        # ====================================================================
        # STAGE 2: Hybrid Results Fusion + LLM Re-ranking (Backend) with Timeout
        # ====================================================================
        logger.info("STAGE 2: Hybrid Results Fusion + LLM Re-ranking")
        fusion_start = time.time()

        try:
            # Use ASYNC version for full LLM re-ranking support
            fusion_result = await asyncio.wait_for(
                components["fusion_engine"].fuse_results_async(
                    all_results=multi_retrieval_result.results,
                    original_query=search_query,  # Use preprocessed query!
                    extracted_entity=None,  # Backend will handle entity extraction if needed
                    required_terms=None
                ),
                timeout=FUSION_TIMEOUT
            )
        except asyncio.TimeoutError:
            fusion_time = time.time() - fusion_start
            logger.error(f"Fusion stage timeout after {fusion_time:.3f}s")
            raise HTTPException(
                status_code=504,
                detail=f"Results fusion timed out after {fusion_time:.1f} seconds. Please try again or contact support."
            )

        fusion_time = time.time() - fusion_start

        # Count unique source documents
        unique_source_docs = len(set(
            doc.filename for doc in fusion_result.fused_results
            if hasattr(doc, 'filename') and doc.filename
        ))

        logger.info(f"✓ Fused to {fusion_result.final_count} chunks from {unique_source_docs} source documents")
        logger.info(f"  Fusion method: {fusion_result.fusion_method}")
        logger.info(f"  Time: {fusion_time:.3f}s")

        if fusion_result.fused_results:
            top_scores = [f"{doc.similarity_score:.3f}" for doc in fusion_result.fused_results[:3]]
            logger.info(f"  Top scores: {top_scores}")

        # ====================================================================
        # STAGE 3: Answer Generation (NEW!) with Timeout
        # ====================================================================
        logger.info("STAGE 3: Answer Generation")
        answer_start = time.time()

        generated_answer = None
        if fusion_result.fused_results:
            # Use QueryEngine to generate natural language answer
            try:
                answer_result = await asyncio.wait_for(
                    components["answer_engine"].generate_answer(
                        query=search_query,
                        retrieved_results=fusion_result.fused_results,
                        original_query=request.query
                    ),
                    timeout=ANSWER_TIMEOUT
                )
                generated_answer = answer_result.answer
                answer_time = time.time() - answer_start
                logger.info(f"✓ Answer generated (confidence: {answer_result.confidence:.3f})")
                logger.info(f"  Time: {answer_time:.3f}s")
                logger.info(f"  Preview: {generated_answer[:100]}...")
            except asyncio.TimeoutError:
                answer_time = time.time() - answer_start
                logger.warning(f"[!] Answer generation timeout after {answer_time:.3f}s")
                logger.info(f"  Time: {answer_time:.3f}s")
                # Continue without answer - still return search results
                generated_answer = None
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

        # Count unique source documents in final results
        unique_final_docs = len(set(
            result.filename for result in search_results
            if hasattr(result, 'filename') and result.filename
        ))

        logger.info("=" * 80)
        logger.info("SEARCH COMPLETED")
        logger.info(f"Total Time: {total_time:.3f}s | Chunks: {len(search_results)} (from {unique_final_docs} source documents)")
        logger.info(f"Breakdown: Retrieval={retrieval_time:.3f}s | Fusion={fusion_time:.3f}s | Answer={answer_time:.3f}s")
        if generated_answer:
            logger.info(f"Answer: {generated_answer[:150]}...")
        logger.info("=" * 80)

        # ====================================================================
        # EMPTY RESULTS: Provide helpful message when no results found
        # ====================================================================
        if len(search_results) == 0:
            logger.info(f"No results found for query: {request.query}")
            helpful_message = ErrorMessageFormatter.format_empty_results_message(request.query)
            # Return response with helpful message in answer field
            generated_answer = helpful_message

        # ====================================================================
        # STAGE 5: Build Performance Metrics
        # ====================================================================
        # Calculate pipeline efficiency percentages
        pipeline_efficiency = PipelineEfficiency(
            extraction_pct=(extraction_time / total_time * 100) if total_time > 0 else 0,
            rewrite_pct=(rewrite_time / total_time * 100) if total_time > 0 else 0,
            retrieval_pct=(retrieval_time / total_time * 100) if total_time > 0 else 0,
            fusion_pct=(fusion_time / total_time * 100) if total_time > 0 else 0,
            answer_pct=(answer_time / total_time * 100) if total_time > 0 else 0
        )

        performance_metrics_obj = PerformanceMetrics(
            total_time=total_time,
            extraction_time=extraction_time,
            rewrite_time=rewrite_time,
            retrieval_time=retrieval_time,
            fusion_time=fusion_time,
            answer_time=answer_time,
            pipeline_efficiency=pipeline_efficiency
        )

        # Build entity result for frontend
        entity_result_obj = EntityResult(
            entity=entity_result_data.entity,
            method=entity_result_data.method,
            confidence=entity_result_data.confidence,
            alternatives=entity_result_data.alternatives if hasattr(entity_result_data, 'alternatives') else []
        )

        # Build rewrite result for frontend
        rewrite_result_obj = RewriteResult(
            original_query=request.query,
            rewrites=rewrite_result_data.rewrites,
            method=rewrite_result_data.method,
            confidence=rewrite_result_data.confidence
        )

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
            },
            # NEW: Entity extraction and query rewriting results
            entity_result=entity_result_obj,
            rewrite_result=rewrite_result_obj,
            performance_metrics=performance_metrics_obj
        )

    except HTTPException:
        # Re-raise HTTPException (e.g., from query validation)
        raise
    except asyncio.TimeoutError:
        total_time = time.time() - start_time
        logger.error(f"Search timeout after {total_time:.3f}s for query: {request.query}")
        raise HTTPException(
            status_code=504,
            detail=f"Search operation timed out after {total_time:.1f} seconds. Please try a simpler query or contact support."
        )
    except ConnectionError as e:
        logger.error(f"Database connection error: {e}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail="Unable to connect to the database. Please try again in a moment."
        )
    except ValueError as e:
        logger.error(f"Invalid value in search operation: {e}", exc_info=True)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid input: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        # Use user-friendly error message
        user_message = ErrorMessageFormatter.format_error(e, user_friendly=True)
        raise HTTPException(
            status_code=500,
            detail=user_message
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
