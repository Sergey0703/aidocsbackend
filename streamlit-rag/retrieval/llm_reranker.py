# retrieval/llm_reranker.py
# LLM-based semantic re-ranking using Gemini API
# Validates search result relevance to prevent false matches like "river" -> "driver"

import logging
import asyncio
import time
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import google.generativeai as genai

logger = logging.getLogger(__name__)


@dataclass
class RelevanceScore:
    """Result of LLM relevance evaluation"""
    score: float  # 0.0 to 10.0
    is_relevant: bool  # True if score >= min_threshold
    reasoning: str = ""  # Optional explanation
    evaluation_time: float = 0.0


class GeminiReranker:
    """
    LLM-based re-ranker using Gemini API for semantic relevance validation.

    This component solves the critical problem where keyword matching produces
    false positives (e.g., searching for "river" returns documents about "driver").

    The re-ranker asks Gemini to evaluate: "Is this result actually relevant to the query?"
    """

    def __init__(self, config):
        """
        Initialize Gemini re-ranker

        Args:
            config: RAGConfig object with llm and search settings
        """
        self.config = config
        self.llm_config = config.llm
        self.search_config = config.search

        # Initialize Gemini API
        if not self.llm_config.api_key:
            raise ValueError("Gemini API key is required for re-ranking")

        genai.configure(api_key=self.llm_config.api_key)

        # Initialize model for re-ranking
        self.model = genai.GenerativeModel(self.llm_config.rerank_model)

        logger.info(f"[*] Gemini reranker initialized: {self.llm_config.rerank_model}")
        logger.info(f"    Batch size: {self.llm_config.rerank_batch_size}")
        logger.info(f"    Min relevance score: {self.llm_config.rerank_min_score}/10")

    async def rerank_results(
        self,
        query: str,
        results: List,
        top_k: Optional[int] = None
    ) -> List:
        """
        Re-rank search results using LLM semantic evaluation.

        Args:
            query: User's search query
            results: List of RetrievalResult objects from hybrid search
            top_k: Return only top K results (default: return all relevant)

        Returns:
            List of RetrievalResult objects filtered and re-ranked by relevance
        """
        if not results:
            logger.info("[*] Reranker: No results to rerank")
            return []

        start_time = time.time()
        logger.info(f"[*] Reranking {len(results)} results for query: '{query}'")

        # Evaluate each result for relevance
        evaluated_results = []

        # Process in batches to avoid rate limiting
        batch_size = self.llm_config.rerank_batch_size
        for i in range(0, len(results), batch_size):
            batch = results[i:i + batch_size]

            # Evaluate batch (sequential to respect rate limits)
            for result in batch:
                try:
                    relevance = await self._evaluate_relevance(query, result)

                    # Add relevance metadata to result
                    if hasattr(result, 'metadata') and result.metadata:
                        result.metadata['llm_relevance_score'] = relevance.score
                        result.metadata['llm_is_relevant'] = relevance.is_relevant
                        result.metadata['llm_reasoning'] = relevance.reasoning
                    else:
                        result.metadata = {
                            'llm_relevance_score': relevance.score,
                            'llm_is_relevant': relevance.is_relevant,
                            'llm_reasoning': relevance.reasoning
                        }

                    # Keep only relevant results
                    filename = result.metadata.get('file_name', 'unknown') if hasattr(result, 'metadata') else 'unknown'
                    if relevance.is_relevant:
                        evaluated_results.append((result, relevance.score))
                        logger.info(f"   [+] Relevant ({relevance.score:.1f}/10): {filename}")
                    else:
                        logger.info(f"   [-] Filtered ({relevance.score:.1f}/10): {filename}")

                except Exception as e:
                    logger.error(f"   [!] Error evaluating result: {e}")
                    # On error, keep result with low score
                    evaluated_results.append((result, 5.0))

            # Rate limiting between batches
            if i + batch_size < len(results):
                await asyncio.sleep(1.0 / self.llm_config.request_rate_limit)

        # Sort by LLM relevance score (descending)
        evaluated_results.sort(key=lambda x: x[1], reverse=True)

        # Apply top_k limit if specified
        if top_k:
            evaluated_results = evaluated_results[:top_k]

        # Extract just the results (without scores)
        reranked_results = [result for result, score in evaluated_results]

        elapsed = time.time() - start_time
        logger.info(f"[+] Reranking complete: {len(results)} -> {len(reranked_results)} results ({elapsed:.2f}s)")
        logger.info(f"    Filtered out {len(results) - len(reranked_results)} irrelevant results")

        return reranked_results

    async def _evaluate_relevance(self, query: str, result) -> RelevanceScore:
        """
        Ask Gemini: "Is this result relevant to the query?"

        Args:
            query: User's search query
            result: RetrievalResult object with content

        Returns:
            RelevanceScore with 0-10 rating and reasoning
        """
        start_time = time.time()

        # Extract content from result
        content = result.content if hasattr(result, 'content') else str(result)

        # Truncate content to avoid token limits (keep first 1500 chars for better context)
        content_preview = content[:1500] + "..." if len(content) > 1500 else content

        # Construct prompt for relevance evaluation
        prompt = f"""You are a search relevance evaluator. Your task is to determine if a search result is truly relevant to the user's query.

QUERY: "{query}"

SEARCH RESULT:
{content_preview}

TASK:
1. Read the query carefully
2. Read the search result carefully
3. Determine if this result is TRULY relevant to the query
4. Consider: Does the result contain information that would help answer the query?
5. Be strict: Substring matches (e.g., "river" in "driver") are NOT relevant

IMPORTANT:
- "river" is NOT relevant to documents about "driver" (substring match)
- "John" is NOT relevant to documents about "Johnson" unless they're about the same person
- Only mark as relevant if the result SEMANTICALLY matches the query intent

OUTPUT FORMAT (respond with ONLY a number 0-10):
- 0-3: Not relevant (false match, substring only, different topic)
- 4-6: Somewhat relevant (tangentially related)
- 7-8: Relevant (contains useful information)
- 9-10: Highly relevant (directly answers query)

Respond with ONLY a single number from 0 to 10:"""

        try:
            # Call Gemini API
            response = self.model.generate_content(
                prompt,
                generation_config={
                    'temperature': self.llm_config.rerank_temperature,
                    'max_output_tokens': self.llm_config.rerank_max_tokens,
                }
            )

            # Parse response
            score_text = response.text.strip()

            # Extract numeric score (handle various formats)
            try:
                # Try direct conversion
                score = float(score_text)
            except ValueError:
                # Try extracting first number from text
                import re
                numbers = re.findall(r'\d+\.?\d*', score_text)
                if numbers:
                    score = float(numbers[0])
                else:
                    logger.warning(f"   [!] Could not parse score from: '{score_text}', defaulting to 5.0")
                    score = 5.0

            # Clamp to 0-10 range
            score = max(0.0, min(10.0, score))

            # Determine if relevant
            is_relevant = score >= self.llm_config.rerank_min_score

            elapsed = time.time() - start_time

            return RelevanceScore(
                score=score,
                is_relevant=is_relevant,
                reasoning=f"LLM score: {score}/10",
                evaluation_time=elapsed
            )

        except Exception as e:
            logger.error(f"   [!] Gemini API error during re-ranking: {e}")
            # On error, return neutral score
            return RelevanceScore(
                score=5.0,
                is_relevant=False,
                reasoning=f"Error: {str(e)}",
                evaluation_time=time.time() - start_time
            )

    def rerank_sync(self, query: str, results: List, top_k: Optional[int] = None) -> List:
        """
        Synchronous wrapper for rerank_results.

        Args:
            query: User's search query
            results: List of RetrievalResult objects
            top_k: Return only top K results

        Returns:
            List of re-ranked results
        """
        try:
            # Check if we're already in an async context
            try:
                loop = asyncio.get_running_loop()
                # We're inside an async context - cannot use sync wrapper
                logger.warning("[!] Already in async context - skipping LLM re-ranking (use async version instead)")
                return results
            except RuntimeError:
                # No running loop - we can create one
                pass

            # Try to get event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # No event loop exists, create one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Run async re-ranking
            try:
                return loop.run_until_complete(self.rerank_results(query, results, top_k))
            except Exception as e:
                logger.error(f"[!] LLM re-ranking execution failed: {e}")
                return results

        except Exception as e:
            logger.error(f"[!] LLM re-ranking setup failed: {e}")
            return results
