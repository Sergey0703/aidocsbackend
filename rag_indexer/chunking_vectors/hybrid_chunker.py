#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hybrid Chunker Wrapper for Docling HybridChunker
Provides integration between Docling's structure-aware chunking and LlamaIndex workflow
"""

import logging
import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path

# Docling imports
from docling_core.types import DoclingDocument

logger = logging.getLogger(__name__)


class HybridChunkerWrapper:
    """
    Wrapper around Docling HybridChunker for integration with LlamaIndex pipeline

    Features:
    - Structure-aware chunking (preserves tables, lists, headings)
    - Token-aware splitting (respects tokenizer limits)
    - Contextual enrichment (optional heading hierarchy)
    - Metadata preservation (registry_id, file_name, etc.)
    """

    def __init__(self, config):
        """
        Initialize Hybrid Chunker

        Args:
            config: Configuration object with hybrid chunking settings
        """
        self.config = config
        self.chunker = None
        self.tokenizer = None
        self.stats = {
            'documents_processed': 0,
            'chunks_created': 0,
            'markdown_conversions': 0,
            'markdown_fallback_used': 0,
            'contextualized_chunks': 0,
            'errors': 0
        }

        self._initialize_tokenizer()
        self._initialize_chunker()

    def _initialize_tokenizer(self):
        """Initialize tokenizer based on config"""
        try:
            hybrid_settings = self.config.get_hybrid_chunking_settings()
            tokenizer_type = hybrid_settings['tokenizer']
            tokenizer_model = hybrid_settings['tokenizer_model']
            max_tokens = hybrid_settings['max_tokens']

            if tokenizer_type == 'huggingface':
                from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
                from transformers import AutoTokenizer

                logger.info(f"Initializing HuggingFace tokenizer: {tokenizer_model}")
                hf_tokenizer = AutoTokenizer.from_pretrained(tokenizer_model)

                self.tokenizer = HuggingFaceTokenizer(
                    tokenizer=hf_tokenizer,
                    max_tokens=max_tokens
                )

            elif tokenizer_type == 'openai':
                import tiktoken
                from docling_core.transforms.chunker.tokenizer.openai import OpenAITokenizer

                logger.info(f"Initializing OpenAI tokenizer: {tokenizer_model}")
                tiktoken_encoder = tiktoken.encoding_for_model(tokenizer_model)

                self.tokenizer = OpenAITokenizer(
                    tokenizer=tiktoken_encoder,
                    max_tokens=max_tokens
                )
            else:
                raise ValueError(f"Unknown tokenizer type: {tokenizer_type}")

            logger.info(f"[+] Tokenizer initialized: {tokenizer_type} (max_tokens={max_tokens})")

        except Exception as e:
            logger.error(f"Failed to initialize tokenizer: {e}")
            raise

    def _initialize_chunker(self):
        """Initialize Docling HybridChunker"""
        try:
            from docling_core.transforms.chunker.hybrid_chunker import HybridChunker

            hybrid_settings = self.config.get_hybrid_chunking_settings()
            merge_peers = hybrid_settings['merge_peers']

            self.chunker = HybridChunker(
                tokenizer=self.tokenizer,
                merge_peers=merge_peers
            )

            logger.info(f"[+] HybridChunker initialized (merge_peers={merge_peers})")

        except Exception as e:
            logger.error(f"Failed to initialize HybridChunker: {e}")
            raise

    def _markdown_to_docling_document(self, markdown_text: str, metadata: Dict[str, Any] = None):
        """
        Convert markdown text to DoclingDocument

        Args:
            markdown_text: Markdown content
            metadata: Optional metadata to attach

        Returns:
            DoclingDocument instance
        """
        try:
            from docling_core.types.doc import (
                DoclingDocument,
                TextItem,
                DocItemLabel,
                GroupItem,
                GroupLabel,
            )

            # Create a new DoclingDocument
            doc = DoclingDocument(name=metadata.get('file_name', 'document') if metadata else 'document')

            # Create main section group for the document
            body_group = GroupItem(
                label=GroupLabel.SECTION,
                name="main",
                parent=None
            )

            # Split markdown into paragraphs (simple splitting by double newlines)
            paragraphs = [p.strip() for p in markdown_text.split('\n\n') if p.strip()]

            # Add each paragraph as a TextItem
            for i, para_text in enumerate(paragraphs):
                if para_text:
                    text_item = TextItem(
                        label=DocItemLabel.PARAGRAPH,
                        text=para_text,
                        parent=body_group,
                        prov=[],
                    )
                    doc.add_item(text_item, parent=body_group)

            # Add the body group to the document
            doc.add_group(body_group)

            # Add metadata if provided
            if metadata:
                for key, value in metadata.items():
                    # Convert UUID to string for JSON compatibility
                    if isinstance(value, uuid.UUID):
                        value = str(value)
                    doc.metadata[key] = value

            self.stats['markdown_conversions'] += 1
            return doc

        except Exception as e:
            logger.error(f"Failed to convert markdown to DoclingDocument: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise

    def _docling_chunk_to_llamaindex_node(self, chunk, source_metadata: Dict[str, Any]):
        """
        Convert Docling chunk to LlamaIndex TextNode

        Args:
            chunk: Docling BaseChunk object
            source_metadata: Original document metadata (registry_id, file_name, etc.)

        Returns:
            LlamaIndex TextNode compatible object
        """
        try:
            from llama_index.core.schema import TextNode

            # Extract chunk text
            chunk_text = chunk.text

            # Build metadata
            node_metadata = {**source_metadata}  # Copy original metadata

            # Add hybrid chunking metadata
            if hasattr(chunk, 'meta') and chunk.meta:
                # Extract doc_items labels
                if hasattr(chunk.meta, 'doc_items') and chunk.meta.doc_items:
                    doc_items_labels = [item.label.value if hasattr(item.label, 'value') else str(item.label)
                                       for item in chunk.meta.doc_items]
                    node_metadata['doc_items'] = doc_items_labels

                    # Determine chunk type based on doc_items
                    if 'TABLE' in doc_items_labels:
                        node_metadata['chunk_type'] = 'table'
                    elif 'LIST' in doc_items_labels:
                        node_metadata['chunk_type'] = 'list'
                    elif len(set(doc_items_labels)) > 2:
                        node_metadata['chunk_type'] = 'mixed'
                    else:
                        node_metadata['chunk_type'] = 'text'

                # Extract heading hierarchy (if available)
                if hasattr(chunk.meta, 'headings') and chunk.meta.headings:
                    node_metadata['headings'] = chunk.meta.headings
                    node_metadata['parent_heading'] = chunk.meta.headings[-1] if chunk.meta.headings else None

            # Add chunking method marker
            node_metadata['chunking_method'] = 'hybrid_docling'

            # Create TextNode
            node = TextNode(
                text=chunk_text,
                metadata=node_metadata,
                id_=str(uuid.uuid4())
            )

            return node

        except Exception as e:
            logger.error(f"Failed to convert chunk to node: {e}")
            raise

    def chunk_documents(self, documents: List) -> List:
        """
        Chunk LlamaIndex documents using Docling HybridChunker

        Args:
            documents: List of LlamaIndex Document objects

        Returns:
            List of LlamaIndex TextNode objects with hybrid chunking
        """
        all_nodes = []
        hybrid_settings = self.config.get_hybrid_chunking_settings()
        use_contextualize = hybrid_settings['use_contextualize']

        logger.info(f"[*] Hybrid chunking {len(documents)} documents...")

        for doc in documents:
            try:
                self.stats['documents_processed'] += 1

                # Preserve original metadata
                source_metadata = doc.metadata if hasattr(doc, 'metadata') else {}

                # Try to load DoclingDocument from JSON (if available)
                docling_doc = None
                json_path = source_metadata.get('json_path')

                if json_path and Path(json_path).exists():
                    try:
                        # Load from JSON (preferred for Hybrid Chunking)
                        docling_doc = DoclingDocument.load_from_json(json_path)
                        logger.debug(f"   Loaded DoclingDocument from JSON: {json_path}")
                    except Exception as e:
                        logger.warning(f"   Failed to load JSON {json_path}: {e}")
                        logger.warning(f"   Falling back to markdown conversion...")

                if docling_doc is None:
                    # Fallback: Convert markdown to DoclingDocument (less accurate)
                    markdown_content = doc.text if hasattr(doc, 'text') else str(doc)
                    docling_doc = self._markdown_to_docling_document(markdown_content, source_metadata)

                # Chunk using HybridChunker
                chunk_iter = self.chunker.chunk(dl_doc=docling_doc)
                chunks = list(chunk_iter)

                logger.debug(f"   Created {len(chunks)} chunks from {source_metadata.get('file_name', 'unknown')}")

                # If JSON produced no chunks, try markdown fallback
                if len(chunks) == 0 and json_path:
                    logger.warning(f"   JSON chunking produced 0 chunks, trying markdown fallback...")
                    markdown_content = doc.text if hasattr(doc, 'text') else str(doc)
                    try:
                        docling_doc = self._markdown_to_docling_document(markdown_content, source_metadata)
                        chunk_iter = self.chunker.chunk(dl_doc=docling_doc)
                        chunks = list(chunk_iter)
                        logger.info(f"   Markdown fallback created {len(chunks)} chunks")
                        self.stats['markdown_fallback_used'] += 1
                    except Exception as fallback_error:
                        logger.error(f"   Markdown fallback also failed: {fallback_error}")
                        self.stats['errors'] += 1
                        continue

                # Convert chunks to LlamaIndex nodes
                for chunk in chunks:
                    # Optionally use contextualized content for embeddings
                    if use_contextualize:
                        try:
                            # Get enriched content (with heading hierarchy)
                            enriched_text = self.chunker.contextualize(chunk=chunk)
                            # Store both versions
                            chunk.text = enriched_text
                            chunk.original_text = chunk.text
                            self.stats['contextualized_chunks'] += 1
                        except Exception as e:
                            logger.warning(f"Failed to contextualize chunk: {e}")

                    # Convert to LlamaIndex node
                    node = self._docling_chunk_to_llamaindex_node(chunk, source_metadata)
                    all_nodes.append(node)
                    self.stats['chunks_created'] += 1

            except Exception as e:
                logger.error(f"Failed to chunk document {doc.metadata.get('file_name', 'unknown')}: {e}")
                self.stats['errors'] += 1
                continue

        logger.info(f"[+] Hybrid chunking complete: {len(all_nodes)} nodes from {len(documents)} documents")
        self._print_stats()

        return all_nodes

    def _print_stats(self):
        """Print chunking statistics"""
        logger.info(f"[*] Hybrid Chunking Stats:")
        logger.info(f"   Documents processed: {self.stats['documents_processed']}")
        logger.info(f"   Total chunks: {self.stats['chunks_created']}")
        logger.info(f"   Markdown conversions: {self.stats['markdown_conversions']}")
        if self.stats['contextualized_chunks'] > 0:
            logger.info(f"   Contextualized chunks: {self.stats['contextualized_chunks']}")
        if self.stats['errors'] > 0:
            logger.warning(f"   Errors: {self.stats['errors']}")


def create_hybrid_chunker(config):
    """
    Factory function to create HybridChunkerWrapper

    Args:
        config: Configuration object

    Returns:
        HybridChunkerWrapper instance
    """
    return HybridChunkerWrapper(config)


# Backward compatibility check
def is_hybrid_chunking_available():
    """
    Check if hybrid chunking dependencies are installed

    Returns:
        bool: True if docling_core with chunking is available
    """
    try:
        from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
        return True
    except ImportError:
        return False


def print_hybrid_chunking_info():
    """Print information about hybrid chunking setup"""
    print("=" * 60)
    print("[*] HYBRID CHUNKING INFORMATION")
    print("=" * 60)

    if is_hybrid_chunking_available():
        print("[+] Docling HybridChunker: AVAILABLE")

        try:
            import docling_core
            version = getattr(docling_core, '__version__', 'unknown')
            print(f"   Version: {version}")
        except:
            pass

        # Check tokenizers
        try:
            import transformers
            print(f"[+] HuggingFace tokenizer: AVAILABLE")
        except ImportError:
            print(f"[!]  HuggingFace tokenizer: NOT AVAILABLE")
            print(f"   Install with: pip install transformers")

        try:
            import tiktoken
            print(f"[+] OpenAI tokenizer: AVAILABLE")
        except ImportError:
            print(f"[!]  OpenAI tokenizer: NOT AVAILABLE")
            print(f"   Install with: pip install tiktoken")
    else:
        print("[-] Docling HybridChunker: NOT AVAILABLE")
        print("   Install with: pip install 'docling-core[chunking]'")

    print("=" * 60)


if __name__ == "__main__":
    # Test hybrid chunking availability
    print_hybrid_chunking_info()

    # Test basic functionality
    if is_hybrid_chunking_available():
        print("\n🧪 Testing HybridChunker initialization...")

        try:
            from chunking_vectors.config import Config
            from llama_index.core import Document

            config = Config()
            config.USE_HYBRID_CHUNKING = True
            config.HYBRID_MAX_TOKENS = 512
            config.HYBRID_TOKENIZER = 'huggingface'
            config.HYBRID_TOKENIZER_MODEL = 'sentence-transformers/all-MiniLM-L6-v2'

            chunker = create_hybrid_chunker(config)

            # Test with simple document
            test_doc = Document(
                text="""
# Test Document

This is a test paragraph.

## Section 1

Another paragraph here with more content to test chunking.

| Column 1 | Column 2 |
|----------|----------|
| Data 1   | Data 2   |
                """,
                metadata={'file_name': 'test.md', 'file_path': '/test/test.md'}
            )

            nodes = chunker.chunk_documents([test_doc])

            print(f"[+] Test successful: Created {len(nodes)} chunks")
            print(f"\nSample chunk metadata:")
            if nodes:
                import json
                print(json.dumps(nodes[0].metadata, indent=2, default=str))

        except Exception as e:
            print(f"[-] Test failed: {e}")
            import traceback
            traceback.print_exc()
