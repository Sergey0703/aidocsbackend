# api/core/dependencies.py
# Dependency injection for FastAPI routes
# Provides singleton instances of system components

import logging
from typing import Dict, Optional
from fastapi import Depends, HTTPException

logger = logging.getLogger(__name__)


class SystemComponents:
    """
    Container for system components with singleton pattern
    Manages initialization and lifecycle of all backend components
    """
    
    _instance: Optional['SystemComponents'] = None
    _components: Optional[Dict] = None
    _initialized: bool = False
    
    def __new__(cls):
        """Singleton pattern - only one instance exists"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def initialize(self):
        """
        Initialize all system components
        This is called once during application startup
        """
        if self._initialized:
            logger.info("⚠️  System components already initialized, skipping...")
            return
        
        if self._components is not None:
            logger.info("⚠️  Components already exist, skipping initialization...")
            return
        
        try:
            logger.info("🔧 Initializing system components...")
            
            # Import backend modules
            from config.settings import config
            from query_processing.entity_extractor import ProductionEntityExtractor
            from query_processing.query_rewriter import ProductionQueryRewriter
            from retrieval.multi_retriever import MultiStrategyRetriever
            from retrieval.results_fusion import HybridResultsFusionEngine
            
            logger.info("📦 Importing components from backend...")
            
            # Initialize entity extractor
            logger.info("  🔤 Initializing Entity Extractor...")
            entity_extractor = ProductionEntityExtractor(config)
            
            # Initialize query rewriter
            logger.info("  ✍️  Initializing Query Rewriter...")
            query_rewriter = ProductionQueryRewriter(config)
            
            # Initialize retriever
            logger.info("  🔍 Initializing Multi-Strategy Retriever...")
            retriever = MultiStrategyRetriever(config)
            
            # Initialize fusion engine
            logger.info("  🔗 Initializing Results Fusion Engine...")
            fusion_engine = HybridResultsFusionEngine(config)
            
            # Store components
            self._components = {
                "entity_extractor": entity_extractor,
                "query_rewriter": query_rewriter,
                "retriever": retriever,
                "fusion_engine": fusion_engine,
                "config": config
            }
            
            self._initialized = True
            
            logger.info("✅ System components initialized successfully")
            logger.info(f"   📊 Components loaded: {list(self._components.keys())}")
            
            # Log component status
            self._log_component_status()
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize system components: {e}", exc_info=True)
            self._components = None
            self._initialized = False
            raise RuntimeError(f"System initialization failed: {e}") from e
    
    def _log_component_status(self):
        """Log status of all initialized components"""
        try:
            logger.info("🔍 Component Status Check:")
            
            # Check entity extractor
            extractors = self._components["entity_extractor"].get_available_extractors()
            logger.info(f"   Entity Extractor: {len(extractors)} methods available - {extractors}")
            
            # Check query rewriter
            rewriter_status = self._components["query_rewriter"].get_rewriter_status()
            logger.info(f"   Query Rewriter: {rewriter_status}")
            
            # Check retriever
            retriever_status = self._components["retriever"].get_retriever_status()
            logger.info(f"   Retriever: {retriever_status}")
            
            # Check config
            config = self._components["config"]
            logger.info(f"   Embedding Model: {config.embedding.model_name}")
            logger.info(f"   LLM Model: {config.llm.main_model}")
            logger.info(f"   Hybrid Search: {'✅ Enabled' if config.search.enable_hybrid_search else '❌ Disabled'}")
            
        except Exception as e:
            logger.warning(f"⚠️  Could not log component status: {e}")
    
    def get_components(self) -> Dict:
        """
        Get initialized components dictionary
        
        Returns:
            dict: Dictionary of initialized components
            
        Raises:
            RuntimeError: If components are not initialized
        """
        if self._components is None:
            logger.error("❌ Components not initialized!")
            raise RuntimeError(
                "System components are not initialized. "
                "This should not happen - check application startup."
            )
        
        return self._components
    
    def is_initialized(self) -> bool:
        """Check if components are initialized"""
        return self._initialized and self._components is not None
    
    def get_component(self, name: str):
        """
        Get a specific component by name
        
        Args:
            name: Component name (e.g., 'entity_extractor', 'retriever')
            
        Returns:
            Component instance
            
        Raises:
            KeyError: If component not found
            RuntimeError: If components not initialized
        """
        components = self.get_components()
        
        if name not in components:
            available = list(components.keys())
            raise KeyError(
                f"Component '{name}' not found. "
                f"Available components: {available}"
            )
        
        return components[name]
    
    def reset(self):
        """
        Reset components (useful for testing)
        WARNING: This will force re-initialization on next access
        """
        logger.warning("⚠️  Resetting system components...")
        self._components = None
        self._initialized = False
        logger.info("✅ Components reset complete")


# Global singleton instance
_system_components = SystemComponents()


def get_system_components() -> SystemComponents:
    """
    FastAPI dependency for getting system components
    
    This is used in route handlers via Depends()
    
    Usage:
        @router.get("/search")
        async def search(
            components: SystemComponents = Depends(get_system_components)
        ):
            comps = components.get_components()
            entity_extractor = comps["entity_extractor"]
            ...
    
    Returns:
        SystemComponents: Singleton instance of system components
        
    Raises:
        HTTPException: If components are not initialized
    """
    if not _system_components.is_initialized():
        logger.error("❌ System components not initialized in dependency!")
        raise HTTPException(
            status_code=503,
            detail="System components are not initialized. Service unavailable."
        )
    
    return _system_components


def initialize_system_components():
    """
    Initialize system components at application startup
    
    This should be called in the FastAPI lifespan event
    
    Usage:
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            initialize_system_components()
            yield
            # Shutdown
    """
    try:
        _system_components.initialize()
    except Exception as e:
        logger.error(f"❌ Failed to initialize system components: {e}")
        raise


def get_entity_extractor():
    """
    Get entity extractor component
    
    FastAPI dependency shortcut
    
    Usage:
        @router.post("/extract")
        async def extract(
            extractor = Depends(get_entity_extractor)
        ):
            result = await extractor.extract_entity(query)
    """
    components = get_system_components()
    return components.get_component("entity_extractor")


def get_query_rewriter():
    """
    Get query rewriter component
    
    FastAPI dependency shortcut
    """
    components = get_system_components()
    return components.get_component("query_rewriter")


def get_retriever():
    """
    Get retriever component
    
    FastAPI dependency shortcut
    """
    components = get_system_components()
    return components.get_component("retriever")


def get_fusion_engine():
    """
    Get fusion engine component
    
    FastAPI dependency shortcut
    """
    components = get_system_components()
    return components.get_component("fusion_engine")


def get_config():
    """
    Get configuration object
    
    FastAPI dependency shortcut
    """
    components = get_system_components()
    return components.get_component("config")


# Health check helper
async def check_system_health() -> Dict:
    """
    Check health of all system components
    
    Returns:
        dict: Health status of each component
    """
    try:
        components = _system_components.get_components()
        
        health_status = {
            "overall": "healthy",
            "components": {}
        }
        
        # Check each component
        for name, component in components.items():
            if name == "config":
                health_status["components"][name] = {
                    "status": "operational",
                    "type": "configuration"
                }
            else:
                # Try to get status method if available
                try:
                    if hasattr(component, 'get_retriever_status'):
                        status = component.get_retriever_status()
                        health_status["components"][name] = {
                            "status": "operational",
                            "details": status
                        }
                    elif hasattr(component, 'get_available_extractors'):
                        extractors = component.get_available_extractors()
                        health_status["components"][name] = {
                            "status": "operational",
                            "extractors": extractors
                        }
                    elif hasattr(component, 'get_rewriter_status'):
                        status = component.get_rewriter_status()
                        health_status["components"][name] = {
                            "status": "operational",
                            "details": status
                        }
                    else:
                        health_status["components"][name] = {
                            "status": "operational",
                            "type": type(component).__name__
                        }
                except Exception as e:
                    logger.warning(f"Could not get detailed status for {name}: {e}")
                    health_status["components"][name] = {
                        "status": "operational",
                        "warning": "status_check_unavailable"
                    }
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "overall": "unhealthy",
            "error": str(e),
            "components": {}
        }


# Validation helpers
def validate_components_initialized():
    """
    Validate that system components are initialized
    
    Raises:
        HTTPException: If components not initialized
    """
    if not _system_components.is_initialized():
        raise HTTPException(
            status_code=503,
            detail="System is not ready. Components are still initializing."
        )


# Component status helper
def get_components_summary() -> Dict:
    """
    Get summary of all components
    
    Returns:
        dict: Summary information about components
    """
    try:
        components = _system_components.get_components()
        
        summary = {
            "initialized": _system_components.is_initialized(),
            "components_count": len(components),
            "components_list": list(components.keys()),
            "backend_modules": {}
        }
        
        # Add module-specific info
        try:
            config = components.get("config")
            if config:
                summary["backend_modules"]["embedding"] = {
                    "model": config.embedding.model_name,
                    "dimension": config.embedding.dimension
                }
                summary["backend_modules"]["llm"] = {
                    "main_model": config.llm.main_model,
                    "extraction_model": config.llm.extraction_model
                }
                summary["backend_modules"]["search"] = {
                    "hybrid_enabled": config.search.enable_hybrid_search,
                    "vector_enabled": config.search.enable_vector_search,
                    "database_enabled": config.search.enable_database_search
                }
        except Exception as e:
            logger.warning(f"Could not get module info: {e}")
        
        return summary
        
    except Exception as e:
        return {
            "initialized": False,
            "error": str(e)
        }