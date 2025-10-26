# retrieval/multi_retriever.py
# Multi-strategy retrieval system with HYBRID SEARCH (Vector + Database)
# UPDATED: Migrated from Ollama to Gemini API
# FIXED: UUID to string conversion with monkey patch
# OPTIMIZED: Removed person name detection - focus on VRN (Vehicle Registration Numbers)

import time
import logging
import asyncio
import re
import uuid
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod
import concurrent.futures
import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

# 🔧 MONKEY PATCH для исправления UUID проблемы в vecs
try:
    import vecs
    from llama_index.core.schema import TextNode
    
    _original_query = vecs.Collection.query
    
    def _patched_query(self, *args, **kwargs):
        """Patched query that converts UUIDs to strings"""
        results = _original_query(self, *args, **kwargs)
        if results:
            for item in results:
                # Convert UUID in metadata (safe way)
                if hasattr(item, 'metadata') and isinstance(item.metadata, dict):
                    for key, value in list(item.metadata.items()):
                        if isinstance(value, uuid.UUID):
                            item.metadata[key] = str(value)
        return results
    
    vecs.Collection.query = _patched_query
    logger.info("✅ Applied UUID monkey patch to vecs.Collection.query")
except Exception as e:
    logger.warning(f"⚠️ Could not apply UUID monkey patch: {e}")


@dataclass
class RetrievalResult:
    """Single retrieval result"""
    content: str
    full_content: str
    filename: str
    similarity_score: float
    metadata: Dict[str, Any]
    source_method: str
    document_id: str = ""
    chunk_index: int = 0
    
    def __post_init__(self):
        if not self.metadata:
            self.metadata = {}


@dataclass
class MultiRetrievalResult:
    """Combined results from multiple retrieval strategies"""
    query: str
    results: List[RetrievalResult]
    methods_used: List[str]
    total_candidates: int
    retrieval_time: float
    fusion_method: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseRetriever(ABC):
    """Base class for retrievers"""
    
    @abstractmethod
    async def retrieve(self, query: str, top_k: int = 10, **kwargs) -> List[RetrievalResult]:
        """Retrieve documents for query"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if retriever is available"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get retriever name"""
        pass


class LlamaIndexRetriever(BaseRetriever):
    """LlamaIndex-based vector retriever - UPDATED for Gemini API"""
    
    def __init__(self, config):
        self.config = config
        self.index = None
        self.embed_model = None
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize LlamaIndex components - UPDATED for Gemini API"""
        try:
            from llama_index.core import VectorStoreIndex, StorageContext
            from llama_index.vector_stores.supabase import SupabaseVectorStore
            from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
            from llama_index.core.retrievers import VectorIndexRetriever
            from llama_index.core.postprocessor import SimilarityPostprocessor
            
            # Initialize embedding model - UPDATED for Gemini API
            self.embed_model = GoogleGenAIEmbedding(
                model_name=self.config.embedding.model_name,
                api_key=self.config.embedding.api_key
            )
            
            # Initialize vector store
            vector_store = SupabaseVectorStore(
                postgres_connection_string=self.config.database.connection_string,
                collection_name=self.config.database.table_name,
                dimension=self.config.embedding.dimension,
            )
            
            # Create storage context
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            
            # Create index
            self.index = VectorStoreIndex.from_vector_store(
                vector_store=vector_store,
                storage_context=storage_context,
                embed_model=self.embed_model
            )
            
            logger.info("✅ LlamaIndex Retriever initialized successfully with Gemini API")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize LlamaIndex Retriever with Gemini: {e}")
            self.index = None
            self.embed_model = None
    
    def is_available(self) -> bool:
        """Check if LlamaIndex components are available"""
        return self.index is not None and self.embed_model is not None
    
    def get_name(self) -> str:
        return "llamaindex_vector"
    
    def _get_smart_threshold(self, query: str, extracted_entity: str = None) -> float:
        """Get smart threshold based on query analysis and config"""
        
        # Check if we have entity-specific config
        if extracted_entity:
            entity_config = self.config.get_entity_config(extracted_entity)
            return entity_config["similarity_threshold"]
        
        # Adaptive threshold based on query complexity
        word_count = len(query.split())
        if word_count <= 2:
            return self.config.search.default_similarity_threshold
        elif word_count >= 6:
            return self.config.search.fallback_similarity_threshold
        else:
            return self.config.search.default_similarity_threshold
    
    def _convert_uuid_to_string(self, value: Any) -> Any:
        """Convert UUID to string recursively in any data structure"""
        if isinstance(value, uuid.UUID):
            return str(value)
        elif isinstance(value, dict):
            return {k: self._convert_uuid_to_string(v) for k, v in value.items()}
        elif isinstance(value, (list, tuple)):
            return type(value)(self._convert_uuid_to_string(item) for item in value)
        else:
            return value
    
    async def retrieve(self, query: str, top_k: int = 10, similarity_threshold: float = None, **kwargs) -> List[RetrievalResult]:
        """Retrieve using LlamaIndex with smart thresholding and UUID fix"""
        if not self.is_available():
            logger.warning("⚠️ LlamaIndex retriever not available")
            return []
        
        # Get smart threshold if not provided
        extracted_entity = kwargs.get('extracted_entity')
        if similarity_threshold is None:
            similarity_threshold = self._get_smart_threshold(query, extracted_entity)
        
        # Respect vector max top_k limit
        actual_top_k = min(top_k, self.config.search.vector_max_top_k)
        
        logger.info(f"🔍 Vector search: '{query}' (threshold: {similarity_threshold}, top_k: {actual_top_k})")
        
        try:
            from llama_index.core.retrievers import VectorIndexRetriever
            from llama_index.core.postprocessor import SimilarityPostprocessor
            
            # Create retriever
            retriever = VectorIndexRetriever(
                index=self.index,
                similarity_top_k=actual_top_k,
                embed_model=self.embed_model
            )
            
            # Create similarity postprocessor
            similarity_postprocessor = SimilarityPostprocessor(
                similarity_cutoff=similarity_threshold
            )
            
            # Retrieve nodes (UUID already fixed by monkey patch)
            nodes = retriever.retrieve(query)
            logger.info(f"   Vector: {len(nodes)} candidates retrieved")
            
            # Apply similarity filtering
            filtered_nodes = similarity_postprocessor.postprocess_nodes(nodes)
            logger.info(f"   Vector: {len(filtered_nodes)} after similarity filter")
            
            # Content validation - DISABLED for RAG Q&A
            # QueryEngine handles relevance internally, no need for aggressive filtering
            validated_nodes = filtered_nodes  # Accept all similarity-filtered nodes

            logger.info(f"   Vector: {len(validated_nodes)} after content validation (disabled for RAG)")
            
            # Convert to RetrievalResult objects
            results = []
            for i, node in enumerate(validated_nodes):
                try:
                    # Extract metadata (UUID already converted by monkey patch)
                    metadata = node.node.metadata if hasattr(node.node, 'metadata') else {}
                    metadata = self._convert_uuid_to_string(metadata)  # Extra safety
                    filename = metadata.get('file_name', 'Unknown')
                    
                    # Get content
                    content = node.node.text if hasattr(node.node, 'text') else str(node.node)
                    
                    # Get similarity score
                    similarity_score = node.score if hasattr(node, 'score') else 0.0
                    
                    # Ensure document_id is string
                    doc_id = metadata.get('id', '')
                    if isinstance(doc_id, uuid.UUID):
                        doc_id = str(doc_id)
                    elif not isinstance(doc_id, str):
                        doc_id = str(doc_id) if doc_id else ''
                    
                    # Ensure chunk_index is int
                    chunk_idx = metadata.get('chunk_index', 0)
                    try:
                        chunk_idx = int(chunk_idx) if chunk_idx is not None else 0
                    except (ValueError, TypeError):
                        chunk_idx = 0
                    
                    result = RetrievalResult(
                        content=content[:500] + "..." if len(content) > 500 else content,
                        full_content=content,
                        filename=filename,
                        similarity_score=similarity_score,
                        metadata=metadata,
                        source_method=self.get_name(),
                        document_id=doc_id,
                        chunk_index=chunk_idx
                    )
                    
                    # Add vector-specific metadata
                    result.metadata.update({
                        "content_validated": True,
                        "smart_threshold_used": similarity_threshold,
                        "query_validated": query
                    })
                    
                    results.append(result)
                    
                except Exception as e:
                    logger.warning(f"Error processing vector node {i}: {e}")
                    continue
            
            logger.info(f"✅ Vector search completed: {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"❌ Vector search failed: {e}")
            return []
    
    def _is_content_relevant(self, query: str, content: str, extracted_entity: str = None) -> bool:
        """
        Smart content relevance check

        UPDATED: Relaxed for RAG Q&A - QueryEngine handles relevance internally
        """

        query_lower = query.lower()
        content_lower = content.lower()

        # For VRN queries - check if entity is in content
        if extracted_entity:
            entity_lower = extracted_entity.lower()
            if entity_lower in content_lower:
                return True

        # RELAXED for RAG Q&A: Accept if ANY significant word matches
        # QueryEngine will handle final relevance determination
        query_words = [word for word in query_lower.split() if len(word) > 2]
        if not query_words:
            return True  # Empty query words - accept

        # Changed from 70% to just 1 word match (very permissive)
        found_words = sum(1 for word in query_words if word in content_lower)
        return found_words >= 1  # At least ONE word match


class DatabaseRetriever(BaseRetriever):
    """🔥 HYBRID DATABASE RETRIEVER - Direct database search for exact matches"""
    
    def __init__(self, config):
        self.config = config
    
    def is_available(self) -> bool:
        """Database retriever is always available"""
        return True
    
    def get_name(self) -> str:
        return "database_hybrid"
    
    async def retrieve(self, query: str, top_k: int = 10, **kwargs) -> List[RetrievalResult]:
        """🔥 Hybrid database search with multiple strategies"""
        logger.info(f"🗄️ Database hybrid search for: '{query}'")
        
        try:
            conn = psycopg2.connect(self.config.database.connection_string)
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            results = []
            
            # Strategy 1: Exact phrase match (highest priority)
            exact_results = await self._exact_phrase_search(cur, query, top_k)
            results.extend(exact_results)
            logger.info(f"   Database: {len(exact_results)} exact phrase matches")
            
            # Strategy 2: Flexible term search (if still need more)
            if len(results) < top_k:
                needed = top_k - len(results)
                terms_results = await self._flexible_terms_search(
                    cur, query, needed,
                    exclude_ids=[r.document_id for r in results]
                )
                results.extend(terms_results)
                logger.info(f"   Database: {len(terms_results)} flexible term matches")
            
            cur.close()
            conn.close()
            
            logger.info(f"✅ Database search completed: {len(results)} total results")
            return results
            
        except Exception as e:
            logger.error(f"❌ Database search failed: {e}")
            return []
    
    async def _exact_phrase_search(self, cur, query: str, limit: int) -> List[RetrievalResult]:
        """Exact phrase matching with high relevance scoring"""
        search_sql = f"""
        SELECT
            id,
            metadata,
            (metadata->>'text') as text_content,
            (metadata->>'file_name') as file_name,
            (metadata->>'chunk_index') as chunk_index
        FROM {self.config.database.schema}.{self.config.database.table_name}
        WHERE (
            -- Word boundary matching: 'river' will NOT match 'driver'
            LOWER(metadata->>'text') ~* %s
            OR
            -- Also try exact phrase matching for multi-word queries
            LOWER(metadata->>'text') LIKE LOWER(%s)
        )
        AND metadata->>'file_name' IS NOT NULL
        ORDER BY LENGTH(metadata->>'text') ASC
        LIMIT %s
        """

        # Use word boundary regex: \m and \M are word boundaries in PostgreSQL
        # \m matches beginning of word, \M matches end of word
        word_boundary_pattern = r'\m' + re.escape(query.lower()) + r'\M'
        phrase_pattern = f"%{query}%"
        cur.execute(search_sql, (word_boundary_pattern, phrase_pattern, limit))
        rows = cur.fetchall()
        
        results = []
        for row in rows:
            try:
                content = row.get('text_content', '')
                if not content:
                    continue
                
                metadata = row.get('metadata', {})
                filename = row.get('file_name') or metadata.get('file_name', 'Unknown')
                
                # Calculate relevance based on query occurrences and content quality
                query_count = content.lower().count(query.lower())
                relevance_score = min(
                    self.config.search.database_exact_match_score,
                    self.config.search.database_base_score + (query_count * self.config.search.database_score_per_occurrence)
                )
                
                # Ensure document_id is string
                doc_id = row.get('id', '')
                if isinstance(doc_id, uuid.UUID):
                    doc_id = str(doc_id)
                elif not isinstance(doc_id, str):
                    doc_id = str(doc_id) if doc_id else ''
                
                # Ensure chunk_index is int
                chunk_idx = row.get('chunk_index', 0)
                try:
                    chunk_idx = int(chunk_idx) if chunk_idx is not None else 0
                except (ValueError, TypeError):
                    chunk_idx = 0
                
                result = RetrievalResult(
                    content=content[:500] + "..." if len(content) > 500 else content,
                    full_content=content,
                    filename=filename,
                    similarity_score=relevance_score,
                    metadata=metadata,
                    source_method=self.get_name(),
                    document_id=doc_id,
                    chunk_index=chunk_idx
                )
                
                result.metadata.update({
                    "match_type": "exact_phrase",
                    "search_query": query,
                    "query_occurrences": query_count,
                    "database_strategy": "exact_phrase"
                })
                
                results.append(result)
                
            except Exception as e:
                logger.warning(f"Error processing exact match: {e}")
                continue
        
        return results
    
    async def _flexible_terms_search(self, cur, query: str, limit: int, exclude_ids: List[str] = None) -> List[RetrievalResult]:
        """Flexible terms matching for broader recall"""
        if exclude_ids is None:
            exclude_ids = []

        # Common stop words to exclude from search
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has',
            'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
            'can', 'this', 'that', 'these', 'those', 'it', 'its', 'what', 'which',
            'who', 'whom', 'where', 'when', 'why', 'how'
        }

        # Extract individual terms (more flexible than exact phrase)
        # Filter by length AND stop words
        terms = [
            term.strip().lower()
            for term in query.split()
            if len(term) > 2 and term.strip().lower() not in stop_words
        ]
        if not terms:
            return []
        
        # Build SQL with OR condition for flexibility
        conditions = []
        params = []
        
        for term in terms:
            conditions.append("LOWER(metadata->>'text') LIKE LOWER(%s)")
            params.append(f"%{term}%")
        
        exclude_condition = ""
        if exclude_ids:
            exclude_ids_str = [str(eid) if not isinstance(eid, str) else eid for eid in exclude_ids]
            placeholders = ','.join(['%s'] * len(exclude_ids_str))
            exclude_condition = f"AND id::text NOT IN ({placeholders})"
            params.extend(exclude_ids_str)
        
        search_sql = f"""
        SELECT 
            id,
            metadata,
            (metadata->>'text') as text_content,
            (metadata->>'file_name') as file_name,
            (metadata->>'chunk_index') as chunk_index
        FROM {self.config.database.schema}.{self.config.database.table_name}
        WHERE ({' OR '.join(conditions)}) {exclude_condition}
        AND metadata->>'file_name' IS NOT NULL
        ORDER BY LENGTH(metadata->>'text') ASC
        LIMIT %s
        """
        
        params.append(limit)
        cur.execute(search_sql, params)
        rows = cur.fetchall()
        
        results = []
        for row in rows:
            try:
                content = row.get('text_content', '')
                if not content:
                    continue
                
                metadata = row.get('metadata', {})
                filename = row.get('file_name') or metadata.get('file_name', 'Unknown')
                
                # Calculate relevance based on term coverage
                relevance_score = self._calculate_terms_relevance(content, terms)
                
                doc_id = str(row.get('id', ''))
                chunk_idx = int(row.get('chunk_index', 0) or 0)
                
                result = RetrievalResult(
                    content=content[:500] + "..." if len(content) > 500 else content,
                    full_content=content,
                    filename=filename,
                    similarity_score=relevance_score,
                    metadata=metadata,
                    source_method=self.get_name(),
                    document_id=doc_id,
                    chunk_index=chunk_idx
                )
                
                result.metadata.update({
                    "match_type": "flexible_terms",
                    "search_terms": terms,
                    "terms_coverage": relevance_score,
                    "database_strategy": "flexible_terms"
                })
                
                results.append(result)
                
            except Exception as e:
                logger.warning(f"Error processing flexible terms match: {e}")
                continue
        
        return results
    
    def _calculate_terms_relevance(self, content: str, terms: List[str]) -> float:
        """Calculate relevance based on term coverage"""
        content_lower = content.lower()
        found_terms = sum(1 for term in terms if term in content_lower)
        
        if found_terms == 0:
            return 0.1
        
        # Base score from coverage
        coverage_score = found_terms / len(terms)
        
        # Boost for multiple occurrences
        total_occurrences = sum(content_lower.count(term) for term in terms)
        occurrence_boost = min(0.2, total_occurrences * 0.02)
        
        base_score = self.config.search.database_base_score * 0.8  # Lower than exact matches
        return min(self.config.search.database_base_score, base_score + coverage_score * 0.2 + occurrence_boost)


class MultiStrategyRetriever:
    """🔥 HYBRID Multi-strategy retriever with Vector + Database search"""
    
    def __init__(self, config):
        self.config = config
        self.retrievers = {}
        self._initialize_retrievers()
    
    def _initialize_retrievers(self):
        """Initialize all available retrievers"""
        # Vector retriever (if enabled) - UPDATED for Gemini
        if self.config.search.enable_vector_search:
            llamaindex_retriever = LlamaIndexRetriever(self.config)
            if llamaindex_retriever.is_available():
                self.retrievers["vector"] = llamaindex_retriever
        
        # Database retriever (if enabled)
        if self.config.search.enable_database_search:
            self.retrievers["database"] = DatabaseRetriever(self.config)
        
        logger.info(f"🔧 Initialized retrievers: {list(self.retrievers.keys())}")
    
    async def multi_retrieve(self, 
                           queries: List[str], 
                           extracted_entity: Optional[str] = None,
                           required_terms: List[str] = None) -> MultiRetrievalResult:
        """🔥 HYBRID multi-strategy retrieval with intelligent strategy selection"""
        start_time = time.time()
        all_results = []
        methods_used = []
        
        primary_query = queries[0] if queries else ""
        
        logger.info(f"🔥 Hybrid multi-strategy retrieval")
        logger.info(f"   Primary query: '{primary_query}'")
        logger.info(f"   Entity: '{extracted_entity}'")
        logger.info(f"   Required terms: {required_terms}")
        
        # Determine optimal search strategy
        search_strategy = self.config.get_search_strategy(primary_query, extracted_entity)
        
        # Get dynamic search parameters
        search_params = self.config.get_dynamic_search_params(primary_query, extracted_entity)
        logger.info(f"🔥 Strategy: {search_strategy}")
        logger.info(f"🔥 Search params: {search_params}")
        
        # 🔥 STRATEGY 1: Database Search (if enabled and appropriate)
        if (self.config.search.enable_database_search and 
            "database" in self.retrievers and
            search_params.get("enable_database_search", True)):
            
            logger.info(f"🗄️ STRATEGY 1: Database search")
            
            # Use extracted entity for database search if available
            db_query = extracted_entity if extracted_entity else primary_query
            logger.info(f"   Database query: '{db_query}'")
            
            database_results = await self.retrievers["database"].retrieve(
                db_query, 
                search_params["top_k"],
                extracted_entity=extracted_entity
            )
            
            if database_results:
                all_results.extend(database_results)
                methods_used.append("database_hybrid")
                logger.info(f"✅ Strategy 1: {len(database_results)} database results")
                
                # Early return if we have enough exact matches
                if search_params.get("database_priority", False) and len(database_results) >= 10:
                    logger.info("🔥 Database priority: sufficient exact matches found, skipping vector search")
                    final_results = database_results[:search_params["top_k"]]
                    
                    return MultiRetrievalResult(
                        query=primary_query,
                        results=final_results,
                        methods_used=methods_used,
                        total_candidates=len(all_results),
                        retrieval_time=time.time() - start_time,
                        fusion_method="database_priority",
                        metadata={
                            "search_params": search_params,
                            "strategy": search_strategy,
                            "early_return": "database_priority"
                        }
                    )
            else:
                logger.info("⚠️ Strategy 1: No database results found")
        
        # 🔥 STRATEGY 2: Vector Search (if enabled)
        if (self.config.search.enable_vector_search and 
            "vector" in self.retrievers):
            
            logger.info(f"🔍 STRATEGY 2: Vector search")
            
            if extracted_entity:
                # Use both entity and original query
                vector_queries = [extracted_entity, primary_query] if extracted_entity != primary_query else [extracted_entity]
                logger.info(f"   Query variants: {vector_queries}")
            else:
                # Use multiple variants
                vector_queries = queries[:2]  # Limit to 2 variants
                logger.info(f"   Query variants: {vector_queries}")
            
            vector_results = await self._retrieve_with_vector_variants(
                vector_queries, 
                search_params["top_k"],
                search_params["similarity_threshold"],
                extracted_entity=extracted_entity
            )
            
            if vector_results:
                all_results.extend(vector_results)
                methods_used.append("vector_smart_threshold")
                logger.info(f"✅ Strategy 2: {len(vector_results)} vector results")
            else:
                logger.info("⚠️ Strategy 2: No vector results found")
        
        # 🔥 STRATEGY 3: Fallback Search (if primary strategies failed)
        if not all_results:
            logger.info(f"⚠️ STRATEGY 3: Fallback search")
            
            # Try with more relaxed parameters
            fallback_params = {
                "top_k": min(50, search_params["top_k"] * 2),
                "similarity_threshold": self.config.search.fallback_similarity_threshold,
                "enable_database_search": True
            }
            
            if "database" in self.retrievers:
                fallback_results = await self.retrievers["database"].retrieve(
                    primary_query, 
                    fallback_params["top_k"]
                )
                
                if fallback_results:
                    all_results.extend(fallback_results)
                    methods_used.append("database_fallback")
                    logger.info(f"✅ Strategy 3: {len(fallback_results)} fallback results")
        
        # Hybrid deduplication and ranking
        final_results = self._hybrid_dedupe_and_rank(all_results, search_params["top_k"], primary_query, extracted_entity)
        
        retrieval_time = time.time() - start_time
        
        logger.info(f"🔥 HYBRID RETRIEVAL COMPLETED:")
        logger.info(f"   Strategy: {search_strategy}")
        logger.info(f"   Total candidates: {len(all_results)}")
        logger.info(f"   Final results: {len(final_results)}")
        logger.info(f"   Methods used: {', '.join(methods_used)}")
        logger.info(f"   Time: {retrieval_time:.3f}s")
        
        return MultiRetrievalResult(
            query=primary_query,
            results=final_results,
            methods_used=methods_used,
            total_candidates=len(all_results),
            retrieval_time=retrieval_time,
            fusion_method="hybrid_multi_strategy",
            metadata={
                "search_params": search_params,
                "strategy": search_strategy,
                "hybrid_enabled": self.config.search.enable_hybrid_search
            }
        )
    
    async def _retrieve_with_vector_variants(self, 
                                           queries: List[str], 
                                           top_k: int, 
                                           similarity_threshold: float,
                                           **kwargs) -> List[RetrievalResult]:
        """Retrieve with query variants using vector search"""
        
        if "vector" not in self.retrievers:
            return []
        
        retriever = self.retrievers["vector"]
        all_results = []
        
        # Process variants sequentially for better control
        for i, query in enumerate(queries[:2]):  # Max 2 variants
            try:
                logger.info(f"   🔍 Vector variant {i+1}: '{query}'")
                
                results = await retriever.retrieve(
                    query, 
                    top_k // len(queries) + 2,  # Distribute top_k across variants
                    similarity_threshold=similarity_threshold,
                    **kwargs
                )
                
                if results:
                    # Add variant metadata
                    for result in results:
                        result.metadata["vector_variant"] = i + 1
                        result.metadata["vector_query"] = query
                    
                    all_results.extend(results)
                    logger.info(f"   ✅ Vector variant {i+1}: {len(results)} results")
                else:
                    logger.info(f"   ⚠️ Vector variant {i+1}: No results")
                    
            except Exception as e:
                logger.warning(f"   ❌ Vector variant {i+1} failed: {e}")
                continue
        
        logger.info(f"🔍 Vector variants summary: {len(all_results)} total results")
        return all_results
    
    def _hybrid_dedupe_and_rank(self, 
                               all_results: List[RetrievalResult], 
                               max_results: int,
                               primary_query: str,
                               extracted_entity: str = None) -> List[RetrievalResult]:
        """🔥 Hybrid deduplication and ranking with source-aware scoring"""
        
        if not all_results:
            return []
        
        # Group by filename for deduplication
        unique_results = {}
        
        for result in all_results:
            file_key = result.filename
            
            if file_key not in unique_results:
                # First occurrence of this file
                unique_results[file_key] = result

            else:
                # Duplicate file - keep the better one
                existing = unique_results[file_key]
                
                # Prefer database results over vector for exact matches
                if result.source_method.startswith("database") and existing.source_method.startswith("vector"):
                    # Database result beats vector result
                    unique_results[file_key] = result
                    result.metadata["dedup_reason"] = "database_priority"
                elif result.similarity_score > existing.similarity_score:
                    # Higher score wins
                    unique_results[file_key] = result
                    result.metadata["dedup_reason"] = "higher_score"
                else:
                    # Keep existing
                    existing.metadata["dedup_reason"] = "kept_existing"
        
        # Apply hybrid scoring
        scored_results = []
        for result in unique_results.values():
            hybrid_score = self._calculate_hybrid_score(result, primary_query, extracted_entity)
            result.metadata["hybrid_score"] = hybrid_score
            scored_results.append(result)
        
        # Sort by hybrid score
        scored_results.sort(key=lambda x: x.metadata.get("hybrid_score", x.similarity_score), reverse=True)
        
        logger.info(f"🔥 Hybrid deduplication: {len(all_results)} → {len(scored_results)} unique → {min(len(scored_results), max_results)} final")
        
        return scored_results[:max_results]
    
    def _calculate_hybrid_score(self, 
                               result: RetrievalResult, 
                               query: str, 
                               extracted_entity: str = None) -> float:
        """🔥 Calculate hybrid score considering source method and query type"""
        
        base_score = result.similarity_score
        
        # Apply source method weights
        if result.source_method.startswith("database"):
            weight = self.config.search.database_result_weight
        else:
            weight = self.config.search.vector_result_weight
        
        weighted_score = base_score * weight
        
        # Apply VRN-specific boosts
        if extracted_entity:
            # Extra boost for exact entity matches in content
            if extracted_entity.lower() in result.full_content.lower():
                weighted_score *= self.config.search.exact_match_boost
        
        # Content quality boost
        content_length = len(result.full_content)
        if 100 <= content_length <= 2000:  # Sweet spot for content length
            weighted_score *= 1.05
        
        # Ensure score stays within reasonable bounds
        return min(1.0, weighted_score)
    
    def get_retriever_status(self) -> Dict[str, bool]:
        """Get status of all retrievers"""
        return {name: retriever.is_available() 
                for name, retriever in self.retrievers.items()}
    
    async def health_check(self) -> Dict[str, Any]:
        """🔥 Comprehensive health check for hybrid retrieval system"""
        health_status = {
            "overall_healthy": True,
            "retrievers": {},
            "config_valid": True,
            "hybrid_enabled": self.config.search.enable_hybrid_search,
            "timestamp": time.time()
        }
        
        # Check each retriever
        for name, retriever in self.retrievers.items():
            try:
                is_available = retriever.is_available()
                health_status["retrievers"][name] = {
                    "available": is_available,
                    "type": retriever.get_name()
                }
                
                if not is_available:
                    health_status["overall_healthy"] = False
                    
            except Exception as e:
                health_status["retrievers"][name] = {
                    "available": False,
                    "error": str(e)
                }
                health_status["overall_healthy"] = False
        
        # Check configuration
        try:
            validation_results = self.config.validate_config()
            invalid_configs = [k for k, v in validation_results.items() if not v]
            
            if invalid_configs:
                health_status["config_valid"] = False
                health_status["config_errors"] = invalid_configs
                health_status["overall_healthy"] = False
                
        except Exception as e:
            health_status["config_valid"] = False
            health_status["config_error"] = str(e)
            health_status["overall_healthy"] = False
        
        return health_status    