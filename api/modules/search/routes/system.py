# api/modules/search/routes/system.py
# System status and health check endpoints

import logging
import psycopg2
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime

from api.modules.search.models.schemas import SystemStatus, HealthCheck
from api.core.dependencies import get_system_components, SystemComponents, check_system_health
from config.settings import config

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthCheck)
async def health_check():
    """
    Simple health check endpoint.
    Returns 200 if service is running.
    """
    return HealthCheck(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now()
    )


@router.get("/status", response_model=SystemStatus)
async def get_status(components: SystemComponents = Depends(get_system_components)):
    """
    Get detailed system status including:
    - Component availability
    - Database connection
    - Embedding model status
    - Hybrid search configuration
    """
    
    try:
        system_components = components.get_components()
        
        # Check database
        database_status = {}
        try:
            conn = psycopg2.connect(config.database.connection_string)
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM {config.database.schema}.{config.database.table_name}")
            total_docs = cur.fetchone()[0]
            cur.execute(f"SELECT COUNT(DISTINCT metadata->>'file_name') FROM {config.database.schema}.{config.database.table_name} WHERE metadata->>'file_name' IS NOT NULL")
            unique_files = cur.fetchone()[0]
            cur.close()
            conn.close()
            
            database_status = {
                "available": True,
                "total_documents": total_docs,
                "unique_files": unique_files
            }
        except Exception as e:
            logger.error(f"Database check failed: {e}")
            database_status = {
                "available": False,
                "error": str(e)
            }
        
        # Check embedding model
        embedding_status = {}
        try:
            logger.info("Testing embedding model...")
            from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
            
            embed_model = GoogleGenAIEmbedding(
                model_name=config.embedding.model_name,
                api_key=config.embedding.api_key
            )
            logger.info(f"Embedding model created: {config.embedding.model_name}")
            
            test_embedding = embed_model.get_text_embedding("test")
            logger.info(f"Test embedding created, dimension: {len(test_embedding)}")
            
            embedding_status = {
                "available": True,
                "model": config.embedding.model_name,
                "dimension": len(test_embedding)
            }
        except Exception as e:
            logger.error(f"Embedding check failed: {e}", exc_info=True)
            embedding_status = {
                "available": False,
                "error": str(e)
            }
        
        # Get component status from health check helper
        component_health = await check_system_health()
        component_status = component_health.get("components", {})
        
        hybrid_enabled = config.search.enable_hybrid_search if hasattr(config.search, 'enable_hybrid_search') else True
        
        return SystemStatus(
            status="operational" if all([
                embedding_status.get("available", False),
                database_status.get("available", False)
            ]) else "degraded",
            components=component_status,
            database=database_status,
            embedding=embedding_status,
            hybrid_enabled=hybrid_enabled,
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Status check failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))