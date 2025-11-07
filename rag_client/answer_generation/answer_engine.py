# answer_generation/answer_engine.py
# Answer Generation Engine using LlamaIndex QueryEngine
# Generates natural language answers from retrieved documents

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AnswerResult:
    """Result from answer generation"""
    answer: str
    source_documents: List[str]
    confidence: float
    metadata: Dict[str, Any]


class AnswerGenerationEngine:
    """
    Answer Generation Engine using LlamaIndex QueryEngine

    According to LlamaIndex documentation:
    - QueryEngine combines retrieval + response synthesis
    - Automatically generates natural language answers
    - Uses LLM to synthesize responses from retrieved context

    Usage:
        engine = AnswerGenerationEngine(config)
        result = await engine.generate_answer(
            query="what VRN we have",
            retrieved_results=[...],
            original_query="what VRN we have"
        )
        print(result.answer)  # Natural language answer!
    """

    def __init__(self, config):
        """
        Initialize Answer Generation Engine

        Args:
            config: Configuration object with LLM and embedding settings
        """
        self.config = config
        self.query_engine = None
        self._initialize_query_engine()

    def _initialize_query_engine(self):
        """
        Initialize LlamaIndex QueryEngine

        Per documentation:
        1. Create VectorStoreIndex from existing vector store
        2. Get QueryEngine via index.as_query_engine()
        3. QueryEngine handles retrieval + answer generation
        """
        try:
            from llama_index.core import VectorStoreIndex, StorageContext
            from llama_index.vector_stores.supabase import SupabaseVectorStore
            from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
            from llama_index.llms.google_genai import GoogleGenAI
            from llama_index.core import Settings

            logger.info("Initializing Answer Generation Engine...")

            # Configure global settings for LlamaIndex
            Settings.llm = GoogleGenAI(
                model=self.config.llm.main_model,
                api_key=self.config.llm.api_key,
                temperature=0.1,  # Low temperature for factual answers
            )

            Settings.embed_model = GoogleGenAIEmbedding(
                model_name=self.config.embedding.model_name,
                api_key=self.config.embedding.api_key,
            )

            # Initialize vector store (connect to existing Supabase collection)
            vector_store = SupabaseVectorStore(
                postgres_connection_string=self.config.database.connection_string,
                collection_name=self.config.database.table_name,
                dimension=self.config.embedding.dimension,
            )

            # Create storage context
            storage_context = StorageContext.from_defaults(vector_store=vector_store)

            # Create index from existing vector store
            index = VectorStoreIndex.from_vector_store(
                vector_store=vector_store,
                storage_context=storage_context,
            )

            # Create QueryEngine with optimized settings
            self.query_engine = index.as_query_engine(
                similarity_top_k=5,  # Retrieve top 5 documents
                response_mode="compact",  # Compact mode for concise answers
                verbose=True,  # Enable logging
            )

            logger.info("Answer Generation Engine initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Answer Generation Engine: {e}")
            self.query_engine = None

    def is_available(self) -> bool:
        """Check if query engine is available"""
        return self.query_engine is not None

    async def generate_answer(
        self,
        query: str,
        retrieved_results: Optional[List] = None,
        original_query: Optional[str] = None
    ) -> AnswerResult:
        """
        Generate natural language answer for query

        Args:
            query: User query (preprocessed or original)
            retrieved_results: Optional pre-retrieved results (not used if QueryEngine does retrieval)
            original_query: Original query before preprocessing

        Returns:
            AnswerResult with natural language answer
        """
        if not self.is_available():
            logger.error("QueryEngine not available")
            return AnswerResult(
                answer="I'm sorry, the answer generation system is currently unavailable.",
                source_documents=[],
                confidence=0.0,
                metadata={"error": "query_engine_not_available"}
            )

        try:
            logger.info(f"Generating answer for query: {query}")

            # Use QueryEngine to generate answer
            # QueryEngine automatically:
            # 1. Retrieves relevant documents
            # 2. Synthesizes natural language answer using LLM
            response = await self.query_engine.aquery(query)

            # Extract source documents
            source_documents = []
            if hasattr(response, 'source_nodes'):
                source_documents = [
                    node.metadata.get('file_name', 'unknown')
                    for node in response.source_nodes
                ]

            # Calculate confidence based on similarity scores
            confidence = 0.0
            if hasattr(response, 'source_nodes') and response.source_nodes:
                # Average similarity score of source nodes
                scores = [
                    node.score if hasattr(node, 'score') else 0.0
                    for node in response.source_nodes
                ]
                confidence = sum(scores) / len(scores) if scores else 0.0

            # Get answer text
            answer = str(response)

            logger.info(f"Answer generated successfully (confidence: {confidence:.3f})")

            return AnswerResult(
                answer=answer,
                source_documents=source_documents,
                confidence=confidence,
                metadata={
                    "original_query": original_query or query,
                    "response_mode": "compact",
                    "num_sources": len(source_documents)
                }
            )

        except Exception as e:
            logger.error(f"Error generating answer: {e}", exc_info=True)
            return AnswerResult(
                answer=f"I encountered an error while generating the answer: {str(e)}",
                source_documents=[],
                confidence=0.0,
                metadata={"error": str(e)}
            )

    def get_status(self) -> Dict[str, Any]:
        """Get engine status"""
        return {
            "available": self.is_available(),
            "llm_model": self.config.llm.main_model if self.config else "unknown",
            "embedding_model": self.config.embedding.model_name if self.config else "unknown",
            "response_mode": "compact"
        }
