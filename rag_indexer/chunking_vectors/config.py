#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simplified Configuration module for RAG Document Indexer (Part 2: Chunking & Vectors Only)
Handles environment variables, validation, and default settings
SIMPLIFIED: Removed all document conversion, OCR, and PDF processing settings
PURPOSE: This module now only handles markdown input → chunking → embeddings → vector storage
"""

import os
from pathlib import Path
from dotenv import load_dotenv


class Config:
    """Simplified configuration class for chunking and vector generation only"""
    
    def __init__(self):
        """Initialize configuration by loading environment variables"""
        load_dotenv()
        self._load_settings()
        self._validate_settings()
    
    def _load_settings(self):
        """Load all settings from environment variables with defaults"""
        
        # --- START ИСПРАВЛЕНИЕ: Используем абсолютные пути ---
        # Вычисляем путь к директории rag_indexer/data относительно этого файла,
        # что делает его независимым от точки запуска.
        base_dir = Path(__file__).resolve().parent.parent / "data"
        project_root = Path(__file__).resolve().parent.parent.parent
        
        # --- DIRECTORY AND FILE SETTINGS ---
        self.DOCUMENTS_DIR = os.getenv("DOCUMENTS_DIR", str(base_dir / "markdown"))
        self.ERROR_LOG_FILE = str(project_root / "logs" / "indexing_errors.log")
        # --- END ИСПРАВЛЕНИЕ ---
        
        # --- BLACKLIST SETTINGS (Keep for excluding logs/temp directories) ---
        # Добавил "_metadata", чтобы сканер индексации не пытался обработать JSON-файлы
        blacklist_env = os.getenv("BLACKLIST_DIRECTORIES", "logs,temp,.git,__pycache__,.vscode,.idea,node_modules,_metadata")
        self.BLACKLIST_DIRECTORIES = [dir.strip() for dir in blacklist_env.split(",") if dir.strip()]
        
        # --- DATABASE SETTINGS ---
        self.CONNECTION_STRING = os.getenv("SUPABASE_CONNECTION_STRING")
        self.TABLE_NAME = os.getenv("TABLE_NAME", "documents")
        
        # --- GEMINI API SETTINGS ---
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        self.EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-004")
        self.EMBED_DIM = int(os.getenv("EMBED_DIM", "768"))
        
        # --- TEXT PROCESSING SETTINGS ---
        self.CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "512"))
        self.CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "128"))
        self.MIN_CHUNK_LENGTH = int(os.getenv("MIN_CHUNK_LENGTH", "50"))

        # --- HYBRID CHUNKING SETTINGS (Docling HybridChunker) ---
        self.USE_HYBRID_CHUNKING = os.getenv("USE_HYBRID_CHUNKING", "false").lower() == "true"
        self.HYBRID_MAX_TOKENS = int(os.getenv("HYBRID_MAX_TOKENS", str(self.CHUNK_SIZE)))
        self.HYBRID_MERGE_PEERS = os.getenv("HYBRID_MERGE_PEERS", "true").lower() == "true"
        self.HYBRID_USE_CONTEXTUALIZE = os.getenv("HYBRID_USE_CONTEXTUALIZE", "false").lower() == "true"
        self.HYBRID_TOKENIZER = os.getenv("HYBRID_TOKENIZER", "huggingface")
        self.HYBRID_TOKENIZER_MODEL = os.getenv("HYBRID_TOKENIZER_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        
        # --- BATCH PROCESSING SETTINGS ---
        self.PROCESSING_BATCH_SIZE = int(os.getenv("PROCESSING_BATCH_SIZE", "50"))
        self.EMBEDDING_BATCH_SIZE = int(os.getenv("BATCH_SIZE", "5"))
        self.DB_BATCH_SIZE = int(os.getenv("DB_BATCH_SIZE", "200"))
        self.NUM_WORKERS = int(os.getenv("NUM_WORKERS", "4"))
        
        # --- PERFORMANCE SETTINGS ---
        self.GEMINI_TIMEOUT = int(os.getenv("GEMINI_TIMEOUT", "300"))
        self.MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
        self.SKIP_VALIDATION = os.getenv("SKIP_VALIDATION", "false").lower() == "true"
        
        # --- GEMINI API OPTIMIZATION SETTINGS ---
        self.GEMINI_REQUEST_RATE_LIMIT = int(os.getenv("GEMINI_REQUEST_RATE_LIMIT", "10"))
        self.GEMINI_RETRY_ATTEMPTS = int(os.getenv("GEMINI_RETRY_ATTEMPTS", "3"))
        self.GEMINI_RETRY_DELAY = float(os.getenv("GEMINI_RETRY_DELAY", "1.0"))
        self.GEMINI_MAX_TOKENS_PER_REQUEST = int(os.getenv("GEMINI_MAX_TOKENS_PER_REQUEST", "2048"))
        
        # --- MONITORING AND LOGGING ---
        self.ENABLE_PROGRESS_LOGGING = os.getenv("ENABLE_PROGRESS_LOGGING", "true").lower() == "true"
        self.LOG_BATCH_TIMING = os.getenv("LOG_BATCH_TIMING", "true").lower() == "true"
        self.LOG_GEMINI_API_CALLS = os.getenv("LOG_GEMINI_API_CALLS", "false").lower() == "true"
    
    def _validate_settings(self):
        """Validate configuration settings and raise errors for critical issues"""
        
        # Critical validations
        if not self.CONNECTION_STRING:
            raise ValueError("SUPABASE_CONNECTION_STRING not found in .env file!")
        
        if not self.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not found in .env file!")
        
        # --- START ИСПРАВЛЕНИЕ: Создаем директории, если их нет ---
        # Проверяем и создаем директории для документов и логов, если они отсутствуют.
        # Это делает приложение более устойчивым к первому запуску.
        docs_path = Path(self.DOCUMENTS_DIR)
        if not docs_path.exists():
            print(f"⚠️ WARNING: Documents directory does not exist: {self.DOCUMENTS_DIR}")
            print(f"   Creating directory...")
            docs_path.mkdir(parents=True, exist_ok=True)
            
        logs_path = Path(self.ERROR_LOG_FILE).parent
        if not logs_path.exists():
            print(f"⚠️ WARNING: Logs directory does not exist: {logs_path}")
            print(f"   Creating directory...")
            logs_path.mkdir(parents=True, exist_ok=True)
        # --- END ИСПРАВЛЕНИЕ ---
        
        # Validate numeric ranges
        if self.CHUNK_SIZE < 100:
            raise ValueError("CHUNK_SIZE must be at least 100")
        
        if self.CHUNK_OVERLAP >= self.CHUNK_SIZE:
            raise ValueError("CHUNK_OVERLAP must be less than CHUNK_SIZE")
        
        # Validate Gemini embedding dimensions
        if self.EMBED_DIM not in [768]:
             print(f"WARNING: Unusual embedding dimension for text-embedding-004: {self.EMBED_DIM}")
             print(f"Recommended dimension for text-embedding-004 is 768.")
        
        if self.PROCESSING_BATCH_SIZE < 1:
            raise ValueError("PROCESSING_BATCH_SIZE must be at least 1")
        
        if self.EMBEDDING_BATCH_SIZE < 1:
            raise ValueError("EMBEDDING_BATCH_SIZE must be at least 1")
        
        if self.DB_BATCH_SIZE < 1:
            raise ValueError("DB_BATCH_SIZE must be at least 1")
        
        # Validate Gemini API settings
        if self.GEMINI_REQUEST_RATE_LIMIT < 1:
            raise ValueError("GEMINI_REQUEST_RATE_LIMIT must be at least 1")
        
        if self.GEMINI_RETRY_ATTEMPTS < 0:
            raise ValueError("GEMINI_RETRY_ATTEMPTS must be 0 or greater")
        
        if self.GEMINI_RETRY_DELAY < 0:
            raise ValueError("GEMINI_RETRY_DELAY must be 0 or greater")
    
    def is_blacklisted_directory(self, directory_path):
        """
        Check if a directory should be excluded from scanning
        
        Args:
            directory_path: Path to check
        
        Returns:
            bool: True if directory should be excluded
        """
        path_parts = str(directory_path).split(os.sep)
        return any(blacklist_dir in path_parts for blacklist_dir in self.BLACKLIST_DIRECTORIES)
    
    def print_config(self):
        """Print current configuration in a readable format"""
        print("=" * 60)
        print("=== SIMPLIFIED RAG INDEXER CONFIGURATION (CHUNKING & VECTORS) ===")
        print(f"Documents directory: {self.DOCUMENTS_DIR} (expects markdown files)")
        print(f"Blacklisted directories: {', '.join(self.BLACKLIST_DIRECTORIES)}")
        print(f"Embedding model: {self.EMBED_MODEL} (Gemini API)")
        print(f"Chunk size: {self.CHUNK_SIZE}, Overlap: {self.CHUNK_OVERLAP}")
        print(f"Vector dimension: {self.EMBED_DIM}")
        print(f"Batch processing: {self.PROCESSING_BATCH_SIZE} chunks per batch")
        print(f"Gemini rate limit: {self.GEMINI_REQUEST_RATE_LIMIT} requests/sec")
        print(f"Gemini API optimization: Rate limit {self.GEMINI_REQUEST_RATE_LIMIT}/sec, {self.GEMINI_RETRY_ATTEMPTS} retries")
        print("=" * 60)
    
    def get_batch_settings(self):
        """Return batch processing settings as a dictionary"""
        return {
            'processing_batch_size': self.PROCESSING_BATCH_SIZE,
            'embedding_batch_size': self.EMBEDDING_BATCH_SIZE,
            'db_batch_size': self.DB_BATCH_SIZE,
            'num_workers': self.NUM_WORKERS
        }
    
    def get_chunk_settings(self):
        """Return text chunking settings as a dictionary"""
        return {
            'chunk_size': self.CHUNK_SIZE,
            'chunk_overlap': self.CHUNK_OVERLAP,
            'min_chunk_length': self.MIN_CHUNK_LENGTH
        }

    def get_hybrid_chunking_settings(self):
        """Return hybrid chunking settings as a dictionary"""
        return {
            'enabled': self.USE_HYBRID_CHUNKING,
            'max_tokens': self.HYBRID_MAX_TOKENS,
            'merge_peers': self.HYBRID_MERGE_PEERS,
            'use_contextualize': self.HYBRID_USE_CONTEXTUALIZE,
            'tokenizer': self.HYBRID_TOKENIZER,
            'tokenizer_model': self.HYBRID_TOKENIZER_MODEL,
        }

    def get_embedding_settings(self):
        """Return Gemini embedding settings as a dictionary"""
        return {
            'model': self.EMBED_MODEL,
            'dimension': self.EMBED_DIM,
            'api_key': self.GEMINI_API_KEY,
            'timeout': self.GEMINI_TIMEOUT,
            'rate_limit': self.GEMINI_REQUEST_RATE_LIMIT,
            'retry_attempts': self.GEMINI_RETRY_ATTEMPTS,
            'retry_delay': self.GEMINI_RETRY_DELAY,
            'max_tokens_per_request': self.GEMINI_MAX_TOKENS_PER_REQUEST
        }
    
    def get_performance_settings(self):
        """Return performance optimization settings as a dictionary"""
        return {
            'max_file_size': self.MAX_FILE_SIZE,
            'skip_validation': self.SKIP_VALIDATION,
            'gemini_timeout': self.GEMINI_TIMEOUT,
            'num_workers': self.NUM_WORKERS,
            'gemini_rate_limit': self.GEMINI_REQUEST_RATE_LIMIT,
            'gemini_retry_attempts': self.GEMINI_RETRY_ATTEMPTS,
            'gemini_retry_delay': self.GEMINI_RETRY_DELAY,
            'max_tokens_per_request': self.GEMINI_MAX_TOKENS_PER_REQUEST
        }
    
    def get_logging_settings(self):
        """Return logging and monitoring settings as a dictionary"""
        return {
            'progress_logging': self.ENABLE_PROGRESS_LOGGING,
            'batch_timing': self.LOG_BATCH_TIMING,
            'gemini_api_calls': self.LOG_GEMINI_API_CALLS
        }


# Global configuration instance
config = Config()


def get_config():
    """Get the global configuration instance"""
    return config


def reload_config():
    """Reload configuration from environment variables"""
    global config
    config = Config()
    return config


def print_feature_status():
    """Print status of simplified features"""
    config = get_config()
    
    print("\n=== SIMPLIFIED FEATURES STATUS (CHUNKING & VECTORS ONLY) ===")
    features = [
        ("Markdown Input Processing", True),
        ("Text Chunking (SentenceSplitter)", True),
        ("Gemini API Embeddings", True),
        ("Vector Storage (Supabase)", True),
        ("Batch Processing", True),
        ("Progress Logging", config.ENABLE_PROGRESS_LOGGING),
        ("Gemini API Logging", config.LOG_GEMINI_API_CALLS),
    ]
    
    for feature_name, enabled in features:
        status = "✓ ENABLED" if enabled else "✗ DISABLED"
        print(f"  {feature_name:<35}: {status}")
    
    print(f"\n🔧 Directory Settings:")
    print(f"  Markdown input directory: {config.DOCUMENTS_DIR}")
    print(f"  Blacklisted directories: {', '.join(config.BLACKLIST_DIRECTORIES)}")
    
    print(f"\n📊 Gemini API Settings:")
    print(f"  Model: {config.EMBED_MODEL}")
    print(f"  Embedding dimension: {config.EMBED_DIM}")
    print(f"  Rate limit: {config.GEMINI_REQUEST_RATE_LIMIT} requests/sec")
    print(f"  Retry attempts: {config.GEMINI_RETRY_ATTEMPTS}")
    print(f"  Timeout: {config.GEMINI_TIMEOUT}s")
    
    print(f"\n📝 Processing Settings:")
    print(f"  Chunk size: {config.CHUNK_SIZE}")
    print(f"  Chunk overlap: {config.CHUNK_OVERLAP}")
    print(f"  Min chunk length: {config.MIN_CHUNK_LENGTH}")
    print(f"  Processing batch size: {config.PROCESSING_BATCH_SIZE}")
    
    print("=" * 50)


def validate_gemini_environment():
    """
    Validate that Gemini API environment is properly configured
    
    Returns:
        dict: Validation results
    """
    config = get_config()
    validation = {
        'gemini_api_key_set': bool(config.GEMINI_API_KEY),
        'configuration_issues': [],
        'warnings': [],
        'ready': False
    }
    
    # Check API key
    if not config.GEMINI_API_KEY:
        validation['configuration_issues'].append("GEMINI_API_KEY not set")
    
    # Check embedding model
    if config.EMBED_MODEL not in ['text-embedding-004']:
        validation['warnings'].append(f"Unusual embedding model: {config.EMBED_MODEL}")
    
    # Check embedding dimension
    if config.EMBED_DIM not in [768]:
        validation['warnings'].append(f"Unusual embedding dimension: {config.EMBED_DIM}")
    
    # Check rate limits
    if config.GEMINI_REQUEST_RATE_LIMIT > 60:
        validation['warnings'].append(f"High rate limit may exceed API quotas: {config.GEMINI_REQUEST_RATE_LIMIT}/sec")
    
    # Check timeout settings
    if config.GEMINI_TIMEOUT < 30:
        validation['warnings'].append(f"Low timeout may cause failures: {config.GEMINI_TIMEOUT}s")
    
    # Determine readiness
    validation['ready'] = len(validation['configuration_issues']) == 0
    
    return validation


def print_gemini_environment_status():
    """Print Gemini API environment status"""
    validation = validate_gemini_environment()
    
    print("\n" + "=" * 60)
    print("🚀 GEMINI API ENVIRONMENT STATUS")
    print("=" * 60)
    
    if validation['ready']:
        print("✅ Gemini API environment is READY")
    else:
        print("❌ Gemini API environment has ISSUES")
    
    if validation['configuration_issues']:
        print("\n⚠️ Configuration Issues:")
        for issue in validation['configuration_issues']:
            print(f"  ❌ {issue}")
    
    if validation['warnings']:
        print("\n⚠️ Warnings:")
        for warning in validation['warnings']:
            print(f"  ⚠️ {warning}")
    
    if validation['ready']:
        print("\n✅ Gemini API key is configured")
        print("✅ Configuration is valid")
        if validation['warnings']:
            print("⚠️ Some warnings present but processing will work")
    
    print("=" * 60)


def get_recommended_gemini_env_vars():
    """
    Get recommended environment variables for Gemini API
    
    Returns:
        dict: Recommended .env settings
    """
    return {
        # Core Gemini settings
        'GEMINI_API_KEY': 'your_gemini_api_key_here',
        'EMBED_MODEL': 'text-embedding-004',
        'EMBED_DIM': '768',
        
        # Performance settings
        'GEMINI_TIMEOUT': '300',
        'GEMINI_REQUEST_RATE_LIMIT': '10',
        'GEMINI_RETRY_ATTEMPTS': '3',
        'GEMINI_RETRY_DELAY': '1.0',
        'GEMINI_MAX_TOKENS_PER_REQUEST': '2048',
        
        # Batch processing
        'PROCESSING_BATCH_SIZE': '50',
        'BATCH_SIZE': '5',
        'DB_BATCH_SIZE': '200',
        
        # Logging
        'LOG_GEMINI_API_CALLS': 'false',
        'ENABLE_PROGRESS_LOGGING': 'true',
        
        # Documents directory (markdown input)
        # Этот путь теперь вычисляется автоматически, но можно переопределить
        'DOCUMENTS_DIR': './rag_indexer/data/markdown',
        
        # Database
        'SUPABASE_CONNECTION_STRING': 'your_connection_string_here',
        'TABLE_NAME': 'documents'
    }


def print_gemini_env_recommendations():
    """Print recommended environment variable settings for Gemini API"""
    recommended = get_recommended_gemini_env_vars()
    
    print("\n" + "=" * 60)
    print("🔧 RECOMMENDED GEMINI API .ENV SETTINGS")
    print("=" * 60)
    print("Add these to your .env file for optimal Gemini API processing:")
    print()
    
    # Group settings by category
    categories = {
        "Core Gemini Settings": [
            'GEMINI_API_KEY',
            'EMBED_MODEL',
            'EMBED_DIM'
        ],
        "Performance Settings": [
            'GEMINI_TIMEOUT',
            'GEMINI_REQUEST_RATE_LIMIT',
            'GEMINI_RETRY_ATTEMPTS',
            'GEMINI_RETRY_DELAY',
            'GEMINI_MAX_TOKENS_PER_REQUEST'
        ],
        "Batch Processing": [
            'PROCESSING_BATCH_SIZE',
            'BATCH_SIZE',
            'DB_BATCH_SIZE'
        ],
        "Logging & Monitoring": [
            'LOG_GEMINI_API_CALLS',
            'ENABLE_PROGRESS_LOGGING'
        ],
        "Input & Database": [
            'DOCUMENTS_DIR',
            'SUPABASE_CONNECTION_STRING',
            'TABLE_NAME'
        ]
    }
    
    for category, vars_list in categories.items():
        print(f"# {category}")
        for var in vars_list:
            if var in recommended:
                print(f"{var}={recommended[var]}")
        print()
    
    print("=" * 60)
    print("💡 Tip: Copy these settings to your .env file and restart the application")
    print("🔑 Important: Replace 'your_gemini_api_key_here' with your actual Gemini API key")
    print("📁 Note: DOCUMENTS_DIR should point to markdown files output from Docling (Part 1)")
    print("=" * 60)


if __name__ == "__main__":
    # Test configuration when run directly
    print("🚀 Simplified RAG Indexer Configuration Test (Gemini API)")
    print("=" * 60)
    
    try:
        config = get_config()
        print("✅ Configuration loaded successfully")
        config.print_config()
        
        # Print feature status
        print_feature_status()
        
        # Check Gemini environment
        print_gemini_environment_status()
        
        # Show recommendations
        print_gemini_env_recommendations()
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        print("Check your .env file and fix any issues")