# retrieval/results_fusion.py
# Advanced results fusion and ranking for hybrid multi-strategy retrieval
# UPDATED: Added LLM re-ranking with Gemini API for semantic validation

import logging
import math
import time
from typing import List, Dict, Optional, Tuple, Any, Set
from dataclasses import dataclass
from collections import defaultdict, Counter
import re

from .llm_reranker import GeminiReranker

logger = logging.getLogger(__name__)

@dataclass
class FusionResult:
    """Result of fusion process"""
    fused_results: List[Any]  # RetrievalResult objects
    fusion_method: str
    original_count: int
    final_count: int
    fusion_metadata: Dict[str, Any]
    fusion_time: float

class HybridResultsFusionEngine:
    """?? Advanced results fusion engine for hybrid retrieval with Vector + Database support"""

    @staticmethod
    def _word_level_match(query: str, text: str) -> bool:
        """
        Check if query matches text at word level (not substring).
        'river' will NOT match 'driver', but WILL match 'river bank'
        """
        if not query or not text:
            return False

        # Escape special regex characters in query
        escaped_query = re.escape(query.lower())

        # Create word boundary pattern: \b matches word boundaries
        pattern = r'\b' + escaped_query + r'\b'

        return bool(re.search(pattern, text.lower()))

    def __init__(self, config):
        self.config = config

        # Initialize LLM re-ranker for semantic validation
        try:
            self.reranker = GeminiReranker(config)
            self.reranking_enabled = True  # ✅ ENABLED - filters irrelevant results
            logger.info("[✅] LLM re-ranking ENABLED with Gemini API")
        except Exception as e:
            logger.warning(f"[!] LLM re-ranking disabled: {e}")
            self.reranker = None
            self.reranking_enabled = False

        # ?? Hybrid fusion weights for different sources
        self.method_weights = {
            # Vector search methods
            "llamaindex_vector": self.config.search.vector_result_weight,
            "vector_search": self.config.search.vector_result_weight,
            "vector_smart_threshold": self.config.search.vector_result_weight,
            
            # Database search methods (higher weights)
            "database_hybrid": self.config.search.database_result_weight,
            "database_exact": self.config.search.database_result_weight,
            "database_direct": self.config.search.database_result_weight,
            
            # Legacy methods
            "hybrid": 1.1,
            "spacy": 0.8
        }
        
        # ?? Strategy-specific boosts
        self.strategy_boosts = {
            "exact_phrase": 1.4,      # Exact phrase matches get highest boost
            "person_name_match": 1.3,  # Person name matches get high boost
            "exact_match": 1.2,       # General exact matches
            "database_only": 1.1,     # Found only by database search
            "vector_better": 1.0,     # Vector was better than database
            "database_better": 1.2,   # Database was better than vector
            "found_by_both": 1.15     # Found by both methods
        }
        
        # ?? Quality indicators for content analysis
        self.quality_indicators = {
            "person_name_exact": self.config.search.exact_match_boost,
            "exact_match": 1.2,
            "high_query_frequency": 1.3,  # Multiple query occurrences
            "optimal_content_length": 1.1, # Good content length (100-2000 chars)
            "recent_document": 1.05,       # Newer documents slight boost
            "training_context": 1.1,       # Training/certification context
            "signature_context": 0.9       # Just signature mention (lower priority)
        }
        
        # ?? Person name detection patterns
        self.person_patterns = [
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # First Last
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # First Middle Last
        ]
        self.person_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.person_patterns]
    
    def fuse_results(self, 
                    all_results: List[Any], 
                    original_query: str,
                    extracted_entity: Optional[str] = None,
                    required_terms: List[str] = None) -> FusionResult:
        """?? Main hybrid fusion method with intelligent strategy selection"""
        
        start_time = time.time()
        
        if not all_results:
            return FusionResult(
                fused_results=[],
                fusion_method="empty",
                original_count=0,
                final_count=0,
                fusion_metadata={"reason": "no_results"},
                fusion_time=time.time() - start_time
            )
        
        original_count = len(all_results)
        
        # ?? Analyze query characteristics for fusion strategy selection
        is_person_query = self._is_person_query(original_query, extracted_entity)
        query_complexity = self._analyze_query_complexity(original_query)
        
        logger.info(f"?? Hybrid fusion: {original_count} results | Person query: {is_person_query} | Complexity: {query_complexity}")
        
        # Remove exact duplicates first
        deduplicated = self._hybrid_deduplication(all_results)
        logger.info(f"   After deduplication: {len(deduplicated)} results")
        
        # ?? Select fusion strategy based on query analysis
        fusion_method = self._select_hybrid_fusion_strategy(
            deduplicated, original_query, is_person_query, query_complexity
        )
        
        # Apply selected fusion method
        if fusion_method == "hybrid_person_priority":
            fused_results = self._hybrid_person_priority_fusion(
                deduplicated, original_query, extracted_entity, required_terms
            )
        elif fusion_method == "hybrid_weighted_fusion":
            fused_results = self._hybrid_weighted_fusion(
                deduplicated, original_query, extracted_entity, required_terms
            )
        elif fusion_method == "database_priority":
            fused_results = self._database_priority_fusion(
                deduplicated, original_query, extracted_entity, required_terms
            )
        elif fusion_method == "vector_priority":
            fused_results = self._vector_priority_fusion(
                deduplicated, original_query, extracted_entity, required_terms
            )
        elif fusion_method == "reciprocal_rank_fusion":
            fused_results = self._reciprocal_rank_fusion(deduplicated, original_query)
        else:
            # Default: hybrid weighted fusion
            fused_results = self._hybrid_weighted_fusion(
                deduplicated, original_query, extracted_entity, required_terms
            )
        
        # Apply final filters and quality checks
        final_results = self._apply_hybrid_final_filters(
            fused_results, original_query, extracted_entity, required_terms, is_person_query
        )

        # [NEW] LLM RE-RANKING: Semantic validation to filter false matches
        if self.reranking_enabled and final_results:
            logger.info(f"[*] Applying LLM re-ranking to validate {len(final_results)} results...")
            try:
                # Re-rank using Gemini API for semantic relevance
                final_results = self.reranker.rerank_sync(
                    query=original_query,
                    results=final_results,
                    top_k=None  # Return all relevant results, not just top K
                )
                logger.info(f"[+] LLM re-ranking complete: kept {len(final_results)} relevant results")
            except Exception as e:
                logger.error(f"[!] LLM re-ranking failed: {e}")
                # Continue with original results on error

        fusion_time = time.time() - start_time

        logger.info(f"? Hybrid fusion completed: {fusion_method} | {original_count}?{len(final_results)} results in {fusion_time:.3f}s")

        return FusionResult(
            fused_results=final_results,
            fusion_method=fusion_method,
            original_count=original_count,
            final_count=len(final_results),
            fusion_metadata=self._generate_hybrid_fusion_metadata(
                all_results, final_results, fusion_method, is_person_query
            ),
            fusion_time=fusion_time
        )

    async def fuse_results_async(self,
                                 all_results: List[Any],
                                 original_query: str,
                                 extracted_entity: Optional[str] = None,
                                 required_terms: List[str] = None) -> FusionResult:
        """
        ASYNC version of fuse_results() with full LLM re-ranking support.

        Use this version when calling from async context (tests, async API endpoints).
        Enables proper LLM re-ranking without event loop conflicts.
        """
        start_time = time.time()

        if not all_results:
            return FusionResult(
                fused_results=[],
                fusion_method="empty",
                original_count=0,
                final_count=0,
                fusion_metadata={"reason": "no_results"},
                fusion_time=time.time() - start_time
            )

        original_count = len(all_results)

        # Analyze query characteristics for fusion strategy selection
        is_person_query = self._is_person_query(original_query, extracted_entity)
        query_complexity = self._analyze_query_complexity(original_query)

        logger.info(f"[*] Hybrid fusion (async): {original_count} results | Person query: {is_person_query} | Complexity: {query_complexity}")

        # Remove exact duplicates first
        deduplicated = self._hybrid_deduplication(all_results)
        logger.info(f"   After deduplication: {len(deduplicated)} results")

        # Select fusion strategy based on query analysis
        fusion_method = self._select_hybrid_fusion_strategy(
            deduplicated, original_query, is_person_query, query_complexity
        )

        # Apply selected fusion method (all these are sync)
        if fusion_method == "hybrid_person_priority":
            fused_results = self._hybrid_person_priority_fusion(
                deduplicated, original_query, extracted_entity, required_terms
            )
        elif fusion_method == "hybrid_weighted_fusion":
            fused_results = self._hybrid_weighted_fusion(
                deduplicated, original_query, extracted_entity, required_terms
            )
        elif fusion_method == "database_priority":
            fused_results = self._database_priority_fusion(
                deduplicated, original_query, extracted_entity, required_terms
            )
        elif fusion_method == "vector_priority":
            fused_results = self._vector_priority_fusion(
                deduplicated, original_query, extracted_entity, required_terms
            )
        elif fusion_method == "reciprocal_rank_fusion":
            fused_results = self._reciprocal_rank_fusion(deduplicated, original_query)
        else:
            # Default: hybrid weighted fusion
            fused_results = self._hybrid_weighted_fusion(
                deduplicated, original_query, extracted_entity, required_terms
            )

        # Apply final filters and quality checks
        final_results = self._apply_hybrid_final_filters(
            fused_results, original_query, extracted_entity, required_terms, is_person_query
        )

        # [NEW] ASYNC LLM RE-RANKING: Full semantic validation
        if self.reranking_enabled and final_results:
            logger.info(f"[*] Applying ASYNC LLM re-ranking to validate {len(final_results)} results...")
            try:
                # Use async re-ranking (no event loop conflicts!)
                final_results = await self.reranker.rerank_results(
                    query=original_query,
                    results=final_results,
                    top_k=None  # Return all relevant results, not just top K
                )
                logger.info(f"[+] ASYNC LLM re-ranking complete: kept {len(final_results)} relevant results")
            except Exception as e:
                logger.error(f"[!] ASYNC LLM re-ranking failed: {e}")
                import traceback
                logger.error(traceback.format_exc())
                # Continue with original results on error

        fusion_time = time.time() - start_time

        logger.info(f"[+] Hybrid fusion (async) completed: {fusion_method} | {original_count} -> {len(final_results)} results in {fusion_time:.3f}s")

        return FusionResult(
            fused_results=final_results,
            fusion_method=fusion_method,
            original_count=original_count,
            final_count=len(final_results),
            fusion_metadata=self._generate_hybrid_fusion_metadata(
                all_results, final_results, fusion_method, is_person_query
            ),
            fusion_time=fusion_time
        )

    def _select_hybrid_fusion_strategy(self, 
                                     results: List[Any], 
                                     query: str,
                                     is_person_query: bool,
                                     complexity: str) -> str:
        """?? Intelligently select fusion strategy based on query and results analysis"""
        
        if len(results) <= 1:
            return "single_result"
        
        # Analyze result sources
        source_methods = [r.source_method for r in results]
        has_database_results = any("database" in method for method in source_methods)
        has_vector_results = any("vector" in method or "llamaindex" in method for method in source_methods)
        
        # ?? Person queries with database results ? person priority
        if is_person_query and has_database_results:
            return "hybrid_person_priority"
        
        # ?? Mixed sources ? hybrid weighted fusion
        if has_database_results and has_vector_results:
            return "hybrid_weighted_fusion"
        
        # ?? Only database results ? database priority
        if has_database_results and not has_vector_results:
            return "database_priority"
        
        # ?? Only vector results ? vector priority  
        if has_vector_results and not has_database_results:
            return "vector_priority"
        
        # ?? Complex queries ? reciprocal rank fusion
        if complexity == "complex" and len(set(source_methods)) >= 2:
            return "reciprocal_rank_fusion"
        
        # Default: hybrid weighted
        return "hybrid_weighted_fusion"
    
    def _hybrid_person_priority_fusion(self, 
                                     results: List[Any], 
                                     query: str,
                                     extracted_entity: Optional[str] = None,
                                     required_terms: List[str] = None) -> List[Any]:
        """?? Person-priority fusion: Database exact matches first, then vector semantic matches"""
        
        logger.info(f"?? Person priority fusion for entity: '{extracted_entity or query}'")
        
        database_results = []
        vector_results = []
        other_results = []
        
        # Categorize results by source
        for result in results:
            if "database" in result.source_method:
                database_results.append(result)
            elif "vector" in result.source_method or "llamaindex" in result.source_method:
                vector_results.append(result)
            else:
                other_results.append(result)
        
        logger.info(f"   Categorized: {len(database_results)} database, {len(vector_results)} vector, {len(other_results)} other")
        
        # ?? Priority 1: Database results with person name scoring
        scored_database = []
        for result in database_results:
            person_score = self._calculate_person_priority_score(result, query, extracted_entity)
            result.metadata.update({
                "person_priority_score": person_score,
                "fusion_priority": "database_person",
                "fusion_method": "hybrid_person_priority"
            })
            scored_database.append(result)
        
        # Sort database results by person priority score
        scored_database.sort(key=lambda x: x.metadata["person_priority_score"], reverse=True)
        
        # ?? Priority 2: Vector results with semantic scoring
        scored_vector = []
        for result in vector_results:
            semantic_score = self._calculate_semantic_priority_score(result, query, extracted_entity)
            result.metadata.update({
                "semantic_priority_score": semantic_score,
                "fusion_priority": "vector_semantic",
                "fusion_method": "hybrid_person_priority"
            })
            scored_vector.append(result)
        
        # Sort vector results by semantic priority
        scored_vector.sort(key=lambda x: x.metadata["semantic_priority_score"], reverse=True)
        
        # ?? Priority 3: Other results
        for result in other_results:
            result.metadata.update({
                "fusion_priority": "other",
                "fusion_method": "hybrid_person_priority"
            })
        
        # Combine with person priority: Database first, then vector, then others
        fused_results = scored_database + scored_vector + other_results
        
        logger.info(f"?? Person priority: {len(scored_database)} DB + {len(scored_vector)} vector + {len(other_results)} other")
        
        return fused_results
    
    def _hybrid_weighted_fusion(self, 
                              results: List[Any], 
                              query: str,
                              extracted_entity: Optional[str] = None,
                              required_terms: List[str] = None) -> List[Any]:
        """?? Advanced hybrid weighted fusion with source-aware scoring"""
        
        logger.info(f"?? Hybrid weighted fusion with {len(results)} results")
        
        query_lower = query.lower()
        entity_lower = extracted_entity.lower() if extracted_entity else ""
        required_terms_lower = [term.lower() for term in (required_terms or [])]
        is_person_query = self._is_person_query(query, extracted_entity)
        
        for result in results:
            # ?? Base weight from source method
            method_weight = self.method_weights.get(result.source_method, 1.0)
            
            # ?? Content analysis
            content_lower = f"{result.content} {result.full_content} {result.filename}".lower()
            
            # ?? Start with base similarity score
            base_score = result.similarity_score
            
            # ?? Quality multiplier calculation
            quality_multiplier = 1.0
            
            # ?? Database strategy boost
            if hasattr(result, 'metadata') and result.metadata.get('database_strategy'):
                strategy = result.metadata['database_strategy']
                quality_multiplier *= self.strategy_boosts.get(strategy, 1.0)
            
            # ?? Match type boost
            if hasattr(result, 'metadata') and result.metadata.get('match_type'):
                match_type = result.metadata['match_type']
                quality_multiplier *= self.strategy_boosts.get(match_type, 1.0)
            
            # ?? Exact query match boost (word-level, not substring)
            if self._word_level_match(query_lower, content_lower):
                quality_multiplier *= self.quality_indicators["person_name_exact" if is_person_query else "exact_match"]
            
            # ?? Entity match boost (for person queries, word-level)
            if entity_lower and self._word_level_match(entity_lower, content_lower):
                if is_person_query:
                    quality_multiplier *= self.quality_indicators["person_name_exact"]
                else:
                    quality_multiplier *= 1.2
            
            # ?? Required terms coverage (word-level)
            if required_terms_lower:
                found_terms = sum(1 for term in required_terms_lower if self._word_level_match(term, content_lower))
                term_coverage = found_terms / len(required_terms_lower)
                if term_coverage > 0.5:
                    quality_multiplier *= (1.0 + term_coverage * 0.3)
            
            # ?? Query frequency boost
            if hasattr(result, 'metadata') and result.metadata.get('query_occurrences', 0) > 1:
                occurrences = result.metadata['query_occurrences']
                quality_multiplier *= min(self.quality_indicators["high_query_frequency"], 1.0 + occurrences * 0.1)
            
            # ?? Content length quality
            content_length = len(result.full_content)
            if 100 <= content_length <= 2000:
                quality_multiplier *= self.quality_indicators["optimal_content_length"]
            elif content_length < 50:
                quality_multiplier *= 0.8  # Penalty for very short content
            
            # ?? Context quality analysis
            context_quality = self._analyze_content_context(content_lower, entity_lower, is_person_query)
            quality_multiplier *= context_quality
            
            # ?? Calculate final weighted score
            weighted_score = base_score * method_weight * quality_multiplier
            
            # ?? Store fusion metadata for debugging
            result.metadata.update({
                "hybrid_weighted_score": weighted_score,
                "method_weight": method_weight,
                "quality_multiplier": quality_multiplier,
                "base_score": base_score,
                "context_quality": context_quality,
                "fusion_method": "hybrid_weighted",
                "is_person_query": is_person_query,
                "fusion_factors": {
                    "exact_query_match": self._word_level_match(query_lower, content_lower),
                    "entity_match": self._word_level_match(entity_lower, content_lower) if entity_lower else False,
                    "term_coverage": found_terms / len(required_terms_lower) if required_terms_lower else 0,
                    "query_occurrences": result.metadata.get('query_occurrences', 0),
                    "content_length_optimal": 100 <= content_length <= 2000,
                    "database_strategy": result.metadata.get('database_strategy'),
                    "match_type": result.metadata.get('match_type')
                }
            })
        
        # Sort by weighted score
        sorted_results = sorted(results, key=lambda x: x.metadata.get("hybrid_weighted_score", x.similarity_score), reverse=True)
        
        logger.info(f"?? Hybrid weighted fusion completed: scores range {sorted_results[0].metadata.get('hybrid_weighted_score', 0):.3f} to {sorted_results[-1].metadata.get('hybrid_weighted_score', 0):.3f}")
        
        return sorted_results
    
    def _database_priority_fusion(self, 
                                results: List[Any], 
                                query: str,
                                extracted_entity: Optional[str] = None,
                                required_terms: List[str] = None) -> List[Any]:
        """?? Database priority fusion: Prioritize exact database matches"""
        
        logger.info(f"??? Database priority fusion")
        
        database_results = [r for r in results if "database" in r.source_method]
        other_results = [r for r in results if "database" not in r.source_method]
        
        # Score database results highly
        for result in database_results:
            result.metadata.update({
                "database_priority_score": result.similarity_score * 1.3,  # 30% boost
                "fusion_method": "database_priority"
            })
        
        # Keep other results as-is
        for result in other_results:
            result.metadata.update({
                "database_priority_score": result.similarity_score,
                "fusion_method": "database_priority"
            })
        
        # Sort by database priority score
        all_scored = database_results + other_results
        all_scored.sort(key=lambda x: x.metadata.get("database_priority_score", x.similarity_score), reverse=True)
        
        logger.info(f"??? Database priority: {len(database_results)} DB results prioritized over {len(other_results)} others")
        
        return all_scored
    
    def _vector_priority_fusion(self, 
                              results: List[Any], 
                              query: str,
                              extracted_entity: Optional[str] = None,
                              required_terms: List[str] = None) -> List[Any]:
        """?? Vector priority fusion: Prioritize semantic vector matches"""
        
        logger.info(f"?? Vector priority fusion")
        
        vector_results = [r for r in results if ("vector" in r.source_method or "llamaindex" in r.source_method)]
        other_results = [r for r in results if not ("vector" in r.source_method or "llamaindex" in r.source_method)]
        
        # Score vector results highly
        for result in vector_results:
            result.metadata.update({
                "vector_priority_score": result.similarity_score * 1.2,  # 20% boost
                "fusion_method": "vector_priority"
            })
        
        # Keep other results as-is
        for result in other_results:
            result.metadata.update({
                "vector_priority_score": result.similarity_score,
                "fusion_method": "vector_priority"
            })
        
        # Sort by vector priority score
        all_scored = vector_results + other_results
        all_scored.sort(key=lambda x: x.metadata.get("vector_priority_score", x.similarity_score), reverse=True)
        
        logger.info(f"?? Vector priority: {len(vector_results)} vector results prioritized over {len(other_results)} others")
        
        return all_scored
    
    def _reciprocal_rank_fusion(self, results: List[Any], query: str) -> List[Any]:
        """?? Enhanced reciprocal rank fusion for hybrid results"""
        
        logger.info(f"?? Reciprocal rank fusion with hybrid awareness")
        
        # Group results by method
        method_groups = defaultdict(list)
        for result in results:
            method_groups[result.source_method].append(result)
        
        # Sort each group independently  
        for method in method_groups:
            method_groups[method].sort(key=lambda x: x.similarity_score, reverse=True)
        
        # Calculate RRF scores with hybrid weights
        rrf_scores = {}
        k = 60  # RRF constant
        
        for result in results:
            result_id = self._create_result_id(result)
            
            if result_id not in rrf_scores:
                rrf_scores[result_id] = {
                    "result": result,
                    "rrf_score": 0,
                    "ranks": {},
                    "methods": set(),
                    "hybrid_boost": self.method_weights.get(result.source_method, 1.0)
                }
            
            # Find rank in its method group
            method_list = method_groups[result.source_method]
            try:
                rank = next(i for i, r in enumerate(method_list) if self._create_result_id(r) == result_id) + 1
                rrf_contribution = 1.0 / (k + rank)
                
                # Apply hybrid weight
                hybrid_weight = rrf_scores[result_id]["hybrid_boost"]
                weighted_rrf = rrf_contribution * hybrid_weight
                
                rrf_scores[result_id]["rrf_score"] += weighted_rrf
                rrf_scores[result_id]["ranks"][result.source_method] = rank
                rrf_scores[result_id]["methods"].add(result.source_method)
                
            except (StopIteration, ValueError):
                logger.warning(f"Could not find rank for result in RRF")
        
        # Boost results that appear in multiple methods (especially database + vector)
        for result_id in rrf_scores:
            methods = rrf_scores[result_id]["methods"]
            method_count = len(methods)
            
            if method_count > 1:
                # Extra boost for database + vector combination
                has_database = any("database" in method for method in methods)
                has_vector = any("vector" in method or "llamaindex" in method for method in methods)
                
                if has_database and has_vector:
                    rrf_scores[result_id]["rrf_score"] *= 1.4  # Strong boost for hybrid matches
                else:
                    rrf_scores[result_id]["rrf_score"] *= (1.0 + (method_count - 1) * 0.2)
        
        # Sort by RRF score
        sorted_items = sorted(
            rrf_scores.values(),
            key=lambda x: x["rrf_score"],
            reverse=True
        )
        
        # Add RRF metadata to results
        fused_results = []
        for item in sorted_items:
            result = item["result"]
            result.metadata.update({
                "hybrid_rrf_score": item["rrf_score"],
                "method_ranks": item["ranks"],
                "methods_count": len(item["methods"]),
                "hybrid_boost_applied": item["hybrid_boost"],
                "fusion_method": "hybrid_rrf"
            })
            fused_results.append(result)
        
        logger.info(f"?? RRF fusion: Top score {fused_results[0].metadata['hybrid_rrf_score']:.4f}")
        
        return fused_results
    
    def _hybrid_deduplication(self, results: List[Any]) -> List[Any]:
        """Keep all unique chunks per file (professional approach)

        CHANGED: Previously kept only 1 chunk per filename+content_hash
        NOW: Keeps ALL unique content chunks, removing only exact duplicates
        This enables aggregation queries to see all entities in multi-entity documents
        """

        if len(results) <= 1:
            return results

        # Use content hash only for deduplication (not filename)
        # This allows multiple chunks from same file with different content
        unique_results = {}

        for result in results:
            # Create deduplication key based on content only
            content_hash = hash(result.full_content[:200])
            dedup_key = f"{content_hash}"

            if dedup_key not in unique_results:
                unique_results[dedup_key] = result
                result.metadata["dedup_status"] = "original"
            else:
                existing = unique_results[dedup_key]

                # Hybrid-aware conflict resolution
                keep_new = self._should_keep_new_result(existing, result)

                if keep_new:
                    # Keep new result, mark why
                    result.metadata["dedup_status"] = "replaced_existing"
                    result.metadata["replacement_reason"] = self._get_replacement_reason(existing, result)
                    unique_results[dedup_key] = result
                else:
                    # Keep existing, mark why
                    existing.metadata["dedup_status"] = "kept_original"
                    existing.metadata["duplicate_found"] = True

        deduplicated = list(unique_results.values())

        logger.info(f"Hybrid deduplication: {len(results)} → {len(deduplicated)} unique results")

        return deduplicated
    
    def _should_keep_new_result(self, existing: Any, new: Any) -> bool:
        """?? Decide whether to keep new result over existing one"""
        
        # ?? Priority 1: Database beats vector for person queries (if we can detect)
        existing_is_db = "database" in existing.source_method
        new_is_db = "database" in new.source_method
        
        if new_is_db and not existing_is_db:
            return True  # Database result replaces vector result
        if existing_is_db and not new_is_db:
            return False  # Keep existing database result
        
        # ?? Priority 2: Higher similarity score
        if new.similarity_score > existing.similarity_score:
            return True
        
        # ?? Priority 3: Better method weight
        existing_weight = self.method_weights.get(existing.source_method, 1.0)
        new_weight = self.method_weights.get(new.source_method, 1.0)
        
        if new_weight > existing_weight:
            return True
        
        # ?? Priority 4: More metadata/context
        existing_metadata_count = len(existing.metadata)
        new_metadata_count = len(new.metadata)
        
        if new_metadata_count > existing_metadata_count:
            return True
        
        # Default: keep existing
        return False
    
    def _get_replacement_reason(self, existing: Any, new: Any) -> str:
        """?? Get human-readable reason for result replacement"""
        
        if "database" in new.source_method and "database" not in existing.source_method:
            return "database_over_vector"
        elif new.similarity_score > existing.similarity_score:
            return "higher_similarity"
        elif self.method_weights.get(new.source_method, 1.0) > self.method_weights.get(existing.source_method, 1.0):
            return "better_method_weight"
        elif len(new.metadata) > len(existing.metadata):
            return "richer_metadata"
        else:
            return "unknown"
    
    def _apply_hybrid_final_filters(self, 
                                  results: List[Any], 
                                  query: str,
                                  extracted_entity: Optional[str] = None,
                                  required_terms: List[str] = None,
                                  is_person_query: bool = False) -> List[Any]:
        """?? Apply final filters with hybrid-aware logic"""
        
        if not results:
            return results
        
        # ?? Minimum score threshold (UPDATED: More strict to reduce false matches)
        # NOTE: This threshold is less critical now that we have LLM re-ranking
        min_score = max(0.3, results[0].similarity_score * 0.5)  # Increased from 0.1 to 0.3

        # ?? For person queries with database results, still be somewhat permissive
        # but not as extreme as before (0.05 -> 0.25)
        if is_person_query:
            has_database_results = any("database" in r.source_method for r in results)
            if has_database_results:
                min_score = 0.25  # Increased from 0.05 to 0.25 (5x stricter)
        
        filtered_results = []
        for result in results:
            # Check minimum score
            final_score = result.metadata.get("hybrid_weighted_score") or result.similarity_score
            
            if final_score >= min_score:
                filtered_results.append(result)
            else:
                logger.debug(f"   Filtered out: {result.filename} (score: {final_score:.3f} < {min_score:.3f})")
        
        # ?? Maximum results limit
        max_results = self.config.search.max_final_results
        final_results = filtered_results[:max_results]
        
        logger.info(f"?? Hybrid final filtering: {len(results)} ? {len(final_results)} results (min_score: {min_score:.3f})")
        
        return final_results
    
    def _analyze_content_context(self, content_lower: str, entity_lower: str, is_person_query: bool) -> float:
        """?? Analyze content context for quality scoring"""
        
        base_quality = 1.0
        
        if not is_person_query:
            return base_quality
        
        if not entity_lower:
            return base_quality
        
        # Look for training/certification context (positive, word-level)
        training_keywords = ['training', 'certificate', 'certification', 'course', 'completed', 'achieved']
        training_context = sum(1 for keyword in training_keywords if self._word_level_match(keyword, content_lower))
        if training_context > 0:
            base_quality *= self.quality_indicators["training_context"]

        # Look for signature-only context (negative, word-level)
        signature_keywords = ['signature', 'signed', 'form', 'date:', 'location:']
        signature_context = sum(1 for keyword in signature_keywords if self._word_level_match(keyword, content_lower))
        if signature_context >= 2 and training_context == 0:
            base_quality *= self.quality_indicators["signature_context"]
        
        return base_quality
    
    def _is_person_query(self, query: str, extracted_entity: str = None) -> bool:
        """?? Detect if query is about a person"""
        
        if extracted_entity:
            # Check if extracted entity looks like a person name
            for pattern in self.person_regex:
                if pattern.search(extracted_entity):
                    return True
        
        # Check query for person indicators
        person_indicators = ['who is', 'tell me about', 'show me', 'find', 'about']
        query_lower = query.lower()
        
        has_person_indicator = any(indicator in query_lower for indicator in person_indicators)
        has_capitalized_words = bool(re.search(r'\b[A-Z][a-z]+\b', query))
        
        return has_person_indicator and has_capitalized_words
    
    def _analyze_query_complexity(self, query: str) -> str:
        """?? Analyze query complexity for fusion strategy selection"""
        
        word_count = len(query.split())
        
        if word_count <= 3:
            return "simple"
        elif word_count <= 6:
            return "medium" 
        else:
            return "complex"
    
    def _calculate_person_priority_score(self, result: Any, query: str, extracted_entity: str = None) -> float:
        """?? Calculate person priority score for database results"""
        
        base_score = result.similarity_score
        content_lower = result.full_content.lower()
        entity_lower = (extracted_entity or query).lower()
        
        # Start with base score
        priority_score = base_score
        
        # Boost for exact entity matches (word-level)
        if entity_lower and self._word_level_match(entity_lower, content_lower):
            priority_score *= 1.4

        # Boost for training context (word-level)
        training_keywords = ['training', 'certificate', 'certification', 'course', 'completed']
        training_matches = sum(1 for keyword in training_keywords if self._word_level_match(keyword, content_lower))
        if training_matches > 0:
            priority_score *= (1.0 + training_matches * 0.1)
        
        # Boost for query occurrences
        if hasattr(result, 'metadata') and result.metadata.get('query_occurrences', 0) > 1:
            occurrences = result.metadata['query_occurrences']
            priority_score *= min(1.3, 1.0 + occurrences * 0.1)
        
        return min(1.0, priority_score)
    
    def _calculate_semantic_priority_score(self, result: Any, query: str, extracted_entity: str = None) -> float:
        """?? Calculate semantic priority score for vector results"""
        
        base_score = result.similarity_score
        content_length = len(result.full_content)
        
        semantic_score = base_score
        
        # Content length quality
        if 100 <= content_length <= 2000:
            semantic_score *= 1.1
        elif content_length < 50:
            semantic_score *= 0.9
        
        # High similarity boost
        if base_score > 0.7:
            semantic_score *= 1.05
        
        return min(1.0, semantic_score)
    
    def _create_result_id(self, result: Any) -> str:
        """Create unique identifier for result"""
        return f"{result.filename}_{hash(result.full_content[:100])}"
    
    def _generate_hybrid_fusion_metadata(self, 
                                       original_results: List[Any],
                                       final_results: List[Any],
                                       fusion_method: str,
                                       is_person_query: bool) -> Dict[str, Any]:
        """?? Generate comprehensive metadata about hybrid fusion process"""
        
        original_methods = Counter(r.source_method for r in original_results)
        final_methods = Counter(r.source_method for r in final_results)
        
        if final_results:
            scores = []
            for r in final_results:
                # Get the fusion score used for ranking
                fusion_score = (r.metadata.get("hybrid_weighted_score") or 
                              r.metadata.get("person_priority_score") or 
                              r.metadata.get("database_priority_score") or 
                              r.metadata.get("vector_priority_score") or 
                              r.metadata.get("hybrid_rrf_score") or 
                              r.similarity_score)
                scores.append(fusion_score)
            
            avg_score = sum(scores) / len(scores)
            score_range = (min(scores), max(scores))
        else:
            avg_score = 0.0
            score_range = (0.0, 0.0)
        
        # Analyze fusion effectiveness
        database_count = sum(1 for r in final_results if "database" in r.source_method)
        vector_count = sum(1 for r in final_results if ("vector" in r.source_method or "llamaindex" in r.source_method))
        
        return {
            "fusion_method": fusion_method,
            "is_person_query": is_person_query,
            "original_methods": dict(original_methods),
            "final_methods": dict(final_methods),
            "deduplication_ratio": len(final_results) / len(original_results) if original_results else 0,
            "avg_final_score": avg_score,
            "score_range": score_range,
            "quality_distribution": self._analyze_hybrid_quality_distribution(final_results),
            "source_distribution": {
                "database_results": database_count,
                "vector_results": vector_count,
                "other_results": len(final_results) - database_count - vector_count
            },
            "hybrid_effectiveness": {
                "mixed_sources": database_count > 0 and vector_count > 0,
                "database_dominance": database_count > vector_count,
                "vector_dominance": vector_count > database_count,
                "balanced_results": abs(database_count - vector_count) <= 2
            },
            "fusion_quality_indicators": {
                "exact_matches": sum(1 for r in final_results 
                                   if r.metadata.get("match_type") == "exact_phrase"),
                "person_matches": sum(1 for r in final_results 
                                    if r.metadata.get("match_type") == "person_name_match"),
                "semantic_matches": sum(1 for r in final_results 
                                      if "vector" in r.source_method),
                "high_quality_scores": sum(1 for r in final_results 
                                         if r.similarity_score >= 0.7)
            }
        }
    
    def _analyze_hybrid_quality_distribution(self, results: List[Any]) -> Dict[str, int]:
        """?? Analyze quality distribution of hybrid fusion results"""
        if not results:
            return {"excellent": 0, "good": 0, "moderate": 0, "low": 0}
        
        distribution = {"excellent": 0, "good": 0, "moderate": 0, "low": 0}
        
        for result in results:
            # Get the best available score
            score = (result.metadata.get("hybrid_weighted_score") or 
                    result.metadata.get("person_priority_score") or 
                    result.similarity_score)
            
            if score >= 0.8:
                distribution["excellent"] += 1
            elif score >= 0.6:
                distribution["good"] += 1
            elif score >= 0.4:
                distribution["moderate"] += 1
            else:
                distribution["low"] += 1
        
        return distribution


# Legacy compatibility class
class ResultsFusionEngine(HybridResultsFusionEngine):
    """?? Legacy compatibility wrapper for the hybrid fusion engine"""
    
    def __init__(self, config):
        super().__init__(config)
        logger.info("?? Using legacy ResultsFusionEngine interface - redirecting to HybridResultsFusionEngine")