# config/settings.py
# Configuration settings for Production RAG System with Hybrid Search
# UPDATED: Migrated from Ollama to Gemini API

import os
from dataclasses import dataclass
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

@dataclass
class DatabaseConfig:
    """Database connection configuration"""
    connection_string: str
    table_name: str = "documents"
    schema: str = "vecs"

@dataclass
class EmbeddingConfig:
    """Embedding model configuration - UPDATED for Gemini API"""
    model_name: str = "text-embedding-004"
    dimension: int = 768
    api_key: str = None

@dataclass
class LLMConfig:
    """LLM configuration for various purposes - UPDATED for Gemini API"""
    # Gemini API key (shared across all LLM operations)
    api_key: str = None
    
    # Main LLM for answer generation
    main_model: str = "gemini-2.0-flash-exp"
    main_timeout: float = 60.0

    # Entity extraction LLM (more precise)
    extraction_model: str = "gemini-2.0-flash-exp"
    extraction_timeout: float = 30.0
    extraction_temperature: float = 0.0
    extraction_max_tokens: int = 50  # Увеличено с 10 до 50 для Gemini

    # Query rewriting LLM (creative)
    rewrite_model: str = "gemini-2.0-flash-exp"
    rewrite_timeout: float = 20.0
    rewrite_temperature: float = 0.3
    rewrite_max_tokens: int = 150  # Увеличено со 100 до 150 для Gemini

    # Re-ranking LLM (semantic relevance validation)
    rerank_model: str = "gemini-2.0-flash-exp"  # Fast experimental model for re-ranking
    rerank_timeout: float = 15.0
    rerank_temperature: float = 0.0  # Deterministic for consistency
    rerank_max_tokens: int = 10  # Just need relevance score 0-10
    rerank_batch_size: int = 10  # Process results in batches
    rerank_min_score: float = 2.5  # Minimum relevance score to keep result (0-10 scale, lowered for better recall)

    # Gemini API performance settings
    request_rate_limit: int = 10  # requests per second
    retry_attempts: int = 3
    retry_delay: float = 1.0
    max_tokens_per_request: int = 2048

@dataclass
class SearchConfig:
    """Search and retrieval configuration with Hybrid Search"""
    
    # 🔥 HYBRID SEARCH SETTINGS
    enable_hybrid_search: bool = True
    enable_vector_search: bool = True
    enable_database_search: bool = True
    
    # Vector search thresholds (balanced for precision vs recall)
    default_similarity_threshold: float = 0.50  # Raised for better precision
    entity_similarity_threshold: float = 0.45   # Raised for entity searches
    fallback_similarity_threshold: float = 0.40 # Raised to filter irrelevant results
    
    # Vector search top_k (respecting 1000 limit)
    default_top_k: int = 20
    entity_top_k: int = 50
    complex_query_top_k: int = 30
    vector_max_top_k: int = 1000  # Supabase/vecs hard limit
    
    # 🔥 DATABASE SEARCH SETTINGS
    database_search_enabled: bool = True
    database_max_results: int = 100
    database_exact_match_score: float = 0.95  # High score for exact matches
    database_base_score: float = 0.60         # Base score for database results
    database_score_per_occurrence: float = 0.05  # Bonus per query occurrence

    # 📄 DOCUMENT-AWARE RETRIEVAL
    enable_full_document_retrieval: bool = True  # Fetch ALL chunks when document matched
    full_document_max_chunks: int = 50  # Max chunks per document (safety limit)

    # Multi-query settings
    max_query_variants: int = 3
    enable_query_rewriting: bool = True
    enable_entity_extraction: bool = True
    enable_multi_retrieval: bool = True

    # Results fusion with hybrid support
    min_results_for_fusion: int = 2
    max_final_results: int = 50  # Increased from 20 to allow full documents
    fusion_method: str = "hybrid_weighted"  # Changed from "weighted_score"
    
    # 🔥 HYBRID FUSION WEIGHTS
    vector_result_weight: float = 0.7
    database_result_weight: float = 1.0      # Database gets higher weight
    exact_match_boost: float = 1.3           # Boost for exact entity matches
    person_name_boost: float = 1.2           # Boost for person name queries
    
    # 🔥 SEARCH STRATEGY SELECTION
    person_query_strategy: str = "database_priority"  # Prioritize DB for person names
    general_query_strategy: str = "vector_priority"   # Prioritize vector for general queries
    hybrid_merge_strategy: str = "score_weighted"     # How to merge results

@dataclass
class DomainConfig:
    """Domain boundaries and validation configuration"""
    # Domain description for LLM validation
    domain_name: str = "vehicle documentation search system"

    document_types: List[str] = None

    # Validation prompt template
    validation_prompt_template: str = None

    def __post_init__(self):
        if self.document_types is None:
            self.document_types = [
                "Vehicle registration certificates",
                "Insurance documents",
                "NCT (vehicle inspection) records",
                "Driver information and certifications",
                "Service and maintenance records",
                "Fuel cards and expense reports",
                "Toll receipts and road usage records"
            ]

        if self.validation_prompt_template is None:
            doc_types_str = '\n'.join([f"- {dt}" for dt in self.document_types])
            self.validation_prompt_template = f"""You are a query validator for a {self.domain_name}.

The system contains:
{doc_types_str}

Analyze this search query and determine:
1. Is it a VALID search query? (not random text, gibberish, or meaningless)
2. What is the INTENT? (vehicle_search, person_search, document_search, date_query, or invalid)

Query: "{{query}}"

Respond in this EXACT format:
VALID: yes/no
INTENT: vehicle_search/person_search/document_search/date_query/invalid
CONFIDENCE: 0.0-1.0
REASON: brief explanation"""


@dataclass
class EntityExtractionConfig:
    """Entity extraction configuration"""
    extraction_methods: List[str] = None
    fallback_enabled: bool = True
    validation_enabled: bool = True
    
    # Known entities for special handling (updated for hybrid search)
    known_entities: Dict[str, Dict] = None
    
    # Extraction prompts
    person_extraction_prompt: str = """Extract only the person's name from this question. Return ONLY the name, no other words.

Examples:
- "tell me about John Smith" -> John Smith
- "who is Mary Johnson" -> Mary Johnson  
- "find information about Bob Wilson" -> Bob Wilson
- "show me John Nolan" -> John Nolan
- "John Nolan certifications" -> John Nolan

Question: {query}

Name:"""
    
    def __post_init__(self):
        if self.extraction_methods is None:
            self.extraction_methods = ["llm", "regex", "spacy"]
        
        if self.known_entities is None:
            # Updated with hybrid search parameters
            self.known_entities = {
                "john nolan": {
                    "similarity_threshold": 0.25,  # Lowered for better recall
                    "top_k": 50,
                    "expected_docs": 9,
                    "search_strategy": "hybrid",  # 🔥
                    "database_priority": True     # 🔥
                },
                "breeda daly": {
                    "similarity_threshold": 0.25,
                    "top_k": 50,
                    "expected_docs": 20,          # Updated count!
                    "search_strategy": "hybrid",  # 🔥
                    "database_priority": True     # 🔥
                },
                "bernie loughnane": {
                    "similarity_threshold": 0.25,
                    "top_k": 50,
                    "expected_docs": 5,
                    "search_strategy": "hybrid",  # 🔥
                    "database_priority": True     # 🔥
                }
            }

@dataclass
class QueryRewriteConfig:
    """Query rewriting configuration"""
    enabled: bool = True
    max_rewrites: int = 3
    rewrite_strategies: List[str] = None
    
    # 🔥 HYBRID SEARCH AWARE REWRITING
    hybrid_rewrite_enabled: bool = True
    entity_query_simplification: bool = True  # Simplify person name queries
    
    # Rewrite prompts
    expand_query_prompt: str = """Generate {num_queries} different ways to search for information about this topic. Make each query more specific and focused.

Original query: {query}

Generate {num_queries} search variations:"""
    
    simplify_query_prompt: str = """Simplify this query to extract the core search terms while preserving the meaning.

Complex query: {query}

Simplified query:"""
    
    # 🔥 ENTITY-SPECIFIC REWRITING
    person_query_simplification_prompt: str = """This appears to be a query about a person. Extract just the person's name for the most effective search.

Original query: {query}

Person name:"""
    
    def __post_init__(self):
        if self.rewrite_strategies is None:
            self.rewrite_strategies = ["expand", "simplify", "rephrase", "entity_extract"]  # Added entity_extract

@dataclass
class UIConfig:
    """Streamlit UI configuration"""
    page_title: str = "Production RAG System"
    page_icon: str = "🔍"
    layout: str = "wide"
    sidebar_state: str = "expanded"
    
    # Performance settings
    cache_ttl: int = 300  # 5 minutes
    show_debug_info: bool = True
    show_performance_metrics: bool = True
    show_advanced_settings: bool = True
    
    # 🔥 HYBRID SEARCH UI SETTINGS
    show_search_strategy_info: bool = True
    show_database_results: bool = True
    show_vector_results: bool = True
    show_hybrid_fusion_details: bool = True
    
    # Example queries (updated with expected counts)
    example_queries: List[str] = None
    
    def __post_init__(self):
        if self.example_queries is None:
            self.example_queries = [
                "John Nolan",
                "tell me about John Nolan",
                "show me John Nolan certifications", 
                "who is Breeda Daly",               # Now finds 20 docs!
                "find Breeda Daly training",        # Now finds 20 docs!
                "what certifications does John Nolan have?",
                "give me information about Breeda Daly's courses",
                "Bernie Loughnane documents"
            ]

class ProductionRAGConfig:
    """Main configuration class for Production RAG System with Hybrid Search - UPDATED for Gemini API"""
    
    def __init__(self):
        # Load environment variables
        self.database = DatabaseConfig(
            connection_string=self._get_connection_string(),
            table_name=os.getenv("TABLE_NAME", "documents")
        )

        # Domain configuration (boundaries for query validation)
        self.domain = DomainConfig()

        # UPDATED: Gemini API key for embeddings
        gemini_api_key = self._get_gemini_api_key()

        self.embedding = EmbeddingConfig(
            model_name=os.getenv("EMBED_MODEL", "text-embedding-004"),
            dimension=int(os.getenv("EMBED_DIM", "3072")),
            api_key=gemini_api_key
        )
        
        # UPDATED: Gemini API for LLM operations
        self.llm = LLMConfig(
            api_key=gemini_api_key,
            main_model=os.getenv("MAIN_LLM_MODEL", "gemini-2.0-flash-exp"),
            extraction_model=os.getenv("EXTRACTION_LLM_MODEL", "gemini-2.0-flash-exp"),
            rewrite_model=os.getenv("REWRITE_LLM_MODEL", "gemini-2.0-flash-exp"),
            request_rate_limit=int(os.getenv("GEMINI_REQUEST_RATE_LIMIT", "10")),
            retry_attempts=int(os.getenv("GEMINI_RETRY_ATTEMPTS", "3")),
            retry_delay=float(os.getenv("GEMINI_RETRY_DELAY", "1.0")),
            max_tokens_per_request=int(os.getenv("GEMINI_MAX_TOKENS_PER_REQUEST", "2048"))
        )
        
        self.search = SearchConfig()
        self.entity_extraction = EntityExtractionConfig()
        self.query_rewrite = QueryRewriteConfig()
        self.ui = UIConfig()
    
    def _get_connection_string(self) -> str:
        """Get database connection string from environment"""
        connection_string = (
            os.getenv("SUPABASE_CONNECTION_STRING") or
            os.getenv("DATABASE_URL") or
            os.getenv("POSTGRES_URL")
        )
        
        if not connection_string:
            raise ValueError("No database connection string found in environment variables!")
        
        return connection_string
    
    def _get_gemini_api_key(self) -> str:
        """Get Gemini API key from environment - UPDATED"""
        api_key = os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables!")
        
        return api_key
    
    def validate_config(self) -> Dict[str, bool]:
        """Validate configuration settings"""
        validation_results = {}
        
        # Check database connection
        validation_results["database_config"] = bool(self.database.connection_string)
        
        # Check embedding configuration - UPDATED for Gemini
        validation_results["embedding_config"] = bool(
            self.embedding.model_name and 
            self.embedding.api_key and
            self.embedding.dimension > 0
        )
        
        # Check LLM configuration - UPDATED for Gemini
        validation_results["llm_config"] = bool(
            self.llm.api_key and
            self.llm.main_model and 
            self.llm.extraction_model and
            self.llm.rewrite_model
        )
        
        # Check search configuration
        validation_results["search_config"] = bool(
            0 < self.search.default_similarity_threshold < 1 and
            self.search.default_top_k > 0 and
            self.search.max_query_variants > 0
        )
        
        # 🔥 Validate hybrid search settings
        validation_results["hybrid_search_config"] = bool(
            self.search.enable_hybrid_search and
            (self.search.enable_vector_search or self.search.enable_database_search)
        )
        
        return validation_results
    
    def get_entity_config(self, entity_name: str) -> Dict:
        """Get configuration for specific entity"""
        entity_lower = entity_name.lower()
        
        if entity_lower in self.entity_extraction.known_entities:
            return self.entity_extraction.known_entities[entity_lower]
        
        # Default configuration for unknown entities (hybrid-aware)
        return {
            "similarity_threshold": self.search.default_similarity_threshold,
            "top_k": self.search.default_top_k,
            "expected_docs": None,
            "search_strategy": "hybrid",      # 🔥 Default to hybrid
            "database_priority": False       # 🔥 Default no DB priority
        }
    
    def get_dynamic_search_params(self, query: str, extracted_entity: str = None) -> Dict:
        """Get dynamic search parameters based on query and entity with hybrid support"""
        query_lower = query.lower()
        
        # If we have extracted entity, use its configuration
        if extracted_entity:
            entity_config = self.get_entity_config(extracted_entity)
            return {
                "similarity_threshold": entity_config["similarity_threshold"],
                "top_k": entity_config["top_k"],
                "search_strategy": entity_config.get("search_strategy", "hybrid"),      # 🔥
                "database_priority": entity_config.get("database_priority", True),    # 🔥
                "enable_database_search": True                                          # 🔥
            }
        
        # Dynamic configuration based on query characteristics
        if len(query.split()) >= 4:  # Complex query
            return {
                "similarity_threshold": self.search.fallback_similarity_threshold,
                "top_k": self.search.complex_query_top_k,
                "search_strategy": "vector_priority",     # 🔥
                "database_priority": False,               # 🔥
                "enable_database_search": True            # 🔥
            }
        elif any(word in query_lower for word in ['tell', 'show', 'find', 'give']):  # Question format
            return {
                "similarity_threshold": self.search.entity_similarity_threshold,
                "top_k": self.search.entity_top_k,
                "search_strategy": "hybrid",              # 🔥
                "database_priority": True,                # 🔥
                "enable_database_search": True            # 🔥
            }
        else:  # Simple query
            return {
                "similarity_threshold": self.search.default_similarity_threshold,
                "top_k": self.search.default_top_k,
                "search_strategy": "hybrid",              # 🔥
                "database_priority": False,               # 🔥
                "enable_database_search": True            # 🔥
            }
    
    def get_search_strategy(self, query: str, extracted_entity: str = None) -> str:
        """🔥 Determine optimal search strategy for given query"""
        
        # Person name queries -> database priority
        if extracted_entity or any(word in query.lower() for word in ['who is', 'tell me about', 'show me']):
            return self.search.person_query_strategy
        
        # Complex queries -> vector priority
        if len(query.split()) >= 6:
            return self.search.general_query_strategy
        
        # Default -> hybrid
        return "hybrid"
    
    def is_person_query(self, query: str, extracted_entity: str = None) -> bool:
        """🔥 Detect if query is about a person"""
        if extracted_entity:
            return True
        
        person_indicators = ['who is', 'tell me about', 'show me', 'find', 'about']
        query_lower = query.lower()
        
        # Check for person indicators + capitalized words (likely names)
        has_person_indicator = any(indicator in query_lower for indicator in person_indicators)
        has_capitalized_words = bool([word for word in query.split() if word[0].isupper() and len(word) > 2])
        
        return has_person_indicator and has_capitalized_words

# Global configuration instance
config = ProductionRAGConfig()