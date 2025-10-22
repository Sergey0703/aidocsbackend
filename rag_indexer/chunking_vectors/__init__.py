"""
Part 2: Chunking & Vectors Module
Loads markdown -> chunks -> embeddings -> vector storage
"""

__version__ = "2.0.0"

from .config import get_config, Config
from .markdown_loader import create_markdown_loader
from .chunk_helpers import create_and_filter_chunks_enhanced
from .embedding_processor import create_embedding_processor
from .batch_processor import create_batch_processor
from .database_manager import create_database_manager

__all__ = [
    'get_config',
    'Config',
    'create_markdown_loader',
    'create_and_filter_chunks_enhanced',
    'create_embedding_processor',
    'create_batch_processor',
    'create_database_manager',
]