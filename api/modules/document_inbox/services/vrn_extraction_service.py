#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# api/modules/document_inbox/services/vrn_extraction_service.py
# VRN Extraction Service - extracts Vehicle Registration Numbers from documents

import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Configure logging
logger = logging.getLogger(__name__)


class VRNExtractionService:
    """Service for extracting VRN from document text using regex and AI."""

    def __init__(self):
        """Initializes the VRNExtractionService."""
        self._config = None
        self._openai_client = None
        logger.info("✅ VRNExtractionService initialized")

    def _setup_backend_path(self):
        """Adds the rag_indexer directory to the Python path."""
        try:
            current_file = Path(__file__)
            project_root = current_file.parent.parent.parent.parent.parent
            backend_path = project_root / "rag_indexer"

            if backend_path.exists() and str(backend_path) not in sys.path:
                sys.path.insert(0, str(backend_path))
                logger.debug(f"Added backend path: {backend_path}")
        except Exception as e:
            logger.error(f"Failed to setup backend path: {e}")

    def _get_config(self):
        """Lazy initializes and returns the configuration."""
        if self._config is None:
            self._setup_backend_path()
            from chunking_vectors.config import get_config
            self._config = get_config()
        return self._config

    def _get_openai_client(self):
        """Lazy initializes and returns the OpenAI client."""
        if self._openai_client is None:
            try:
                from openai import OpenAI
                config = self._get_config()
                self._openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
                logger.debug("✅ OpenAI client initialized")
            except ImportError:
                logger.error("OpenAI library not found. Please install it with 'pip install openai'")
                self._openai_client = None
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self._openai_client = None
        return self._openai_client

    # ========================================================================
    # IRISH VRN REGEX PATTERNS
    # ========================================================================

    @staticmethod
    def _get_vrn_patterns() -> List[re.Pattern]:
        """
        Returns a list of compiled regex patterns for Irish VRN formats.

        Irish VRN formats include:
        - Modern (2013+): YY-C-NNNNN (e.g., 191-D-12345, 24-KY-999)
        - Legacy: YY-C-NNNN or C-NNNNN (e.g., 06-D-1234, D-12345)
        """
        return [
            # Modern format: YY(Y)-C-N{1,6} (e.g., 191-D-12345)
            re.compile(r'\b(\d{2,3})-([A-Z]{1,2})-(\d{1,6})\b', re.IGNORECASE),
            # Legacy format: YY-C-N{1,5} (e.g., 06-D-1234)
            re.compile(r'\b(\d{2})-([A-Z]{1,2})-(\d{1,5})\b', re.IGNORECASE),
            # Legacy format: C-N{1,6} (e.g., D-12345)
            re.compile(r'\b([A-Z]{1,2})-(\d{1,6})\b', re.IGNORECASE),
            # Format without dashes: YY(Y)CN{1,6} (e.g., 191D12345)
            re.compile(r'\b(\d{2,3})([A-Z]{1,2})(\d{1,6})\b', re.IGNORECASE),
        ]

    @staticmethod
    def _normalize_vrn(vrn: str) -> str:
        """
        Normalizes a VRN to a standard format with dashes.

        Examples:
            "191D12345" -> "191-D-12345"
            "06 d 1234" -> "06-D-1234"
            "d12345"    -> "D-12345"
        """
        vrn = vrn.upper().strip().replace(' ', '')

        # Return if already in a standard dashed format
        if re.match(r'^\d{2,3}-[A-Z]{1,2}-\d{1,6}$', vrn) or \
           re.match(r'^[A-Z]{1,2}-\d{1,6}$', vrn):
            return vrn

        # Attempt to add dashes to formats like '191D12345'
        match = re.match(r'^(\d{2,3})([A-Z]{1,2})(\d{1,6})$', vrn)
        if match:
            return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"

        # Attempt to add dashes to formats like 'D12345'
        match = re.match(r'^([A-Z]{1,2})(\d{1,6})$', vrn)
        if match:
            return f"{match.group(1)}-{match.group(2)}"

        # Return original if no standard format could be applied
        return vrn

    def extract_vrn_from_text(self, text: str) -> Optional[str]:
        """
        Extracts the first matching VRN from a block of text using regex.

        Args:
            text: The text to search within.

        Returns:
            A normalized VRN string or None if not found.
        """
        if not text:
            return None

        for pattern in self._get_vrn_patterns():
            matches = pattern.findall(text)
            if matches:
                # Reconstruct VRN from the first match's groups
                match_groups = matches[0]
                vrn_raw = ''.join(match_groups) if isinstance(match_groups, tuple) else match_groups
                vrn_normalized = self._normalize_vrn(vrn_raw)
                logger.debug(f"✅ VRN found via regex: {vrn_normalized}")
                return vrn_normalized

        logger.debug("❌ No VRN found via regex")
        return None

    def extract_vrn_from_filename(self, filename: str) -> Optional[str]:
        """
        Extracts a VRN from a filename.

        Examples:
            "191-D-12345_insurance.pdf" -> "191-D-12345"
            "06-D-1234_nct.pdf"        -> "06-D-1234"
        """
        if not filename:
            return None

        for pattern in self._get_vrn_patterns():
            match = pattern.search(filename)
            if match:
                vrn_raw = match.group(0)
                vrn_normalized = self._normalize_vrn(vrn_raw)
                logger.debug(f"✅ VRN found in filename: {vrn_normalized}")
                return vrn_normalized

        return None

    async def extract_vrn_with_ai(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extracts VRN, make, and model from text using the OpenAI API.

        Args:
            text: The document text to analyze.

        Returns:
            A dictionary with 'vrn', 'make', and 'model' or None if extraction fails.
        """
        client = self._get_openai_client()
        if not client:
            logger.warning("OpenAI client not available, skipping AI extraction.")
            return None

        # Use a snippet of text for efficiency
        text_snippet = text[:2000]

        prompt = f"""Extract vehicle information from the following Irish document text.

        Document text:
        "{text_snippet}"

        Extract the following fields:
        1. VRN (Vehicle Registration Number) in an Irish format like "191-D-12345", "06-D-1234", or "D-12345".
        2. Make (the vehicle manufacturer, e.g., "Toyota").
        3. Model (the vehicle model, e.g., "Corolla").

        Respond ONLY with a valid JSON object in the following format:
        {{"vrn": "191-D-12345", "make": "Toyota", "model": "Corolla"}}

        If a field cannot be found, its value should be null. If no vehicle information is found, respond with:
        {{"vrn": null, "make": null, "model": null}}"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a data extraction assistant specializing in Irish vehicle documents. Your response must be only a valid JSON object."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=150
            )

            result_text = response.choices[0].message.content.strip()
            result = json.loads(result_text)

            if result.get('vrn'):
                result['vrn'] = self._normalize_vrn(result['vrn'])
                logger.info(f"✅ AI extracted: VRN={result['vrn']}, Make={result.get('make')}, Model={result.get('model')}")
                return result
            else:
                logger.debug("❌ AI did not find a VRN in the text.")
                return None

        except json.JSONDecodeError as e:
            logger.error(f"AI extraction failed: Invalid JSON response. Error: {e}")
            return None
        except Exception as e:
            logger.error(f"AI extraction failed with an unexpected error: {e}", exc_info=True)
            return None

    # ========================================================================
    # DOCUMENT TEXT RETRIEVAL
    # ========================================================================

    async def _get_document_text(self, filename: str) -> Optional[str]:
        """
        Retrieves the full text of a document from the vecs.documents table.

        Args:
            filename: The document filename (can be a full path or base name).

        Returns:
            The combined text from all document chunks or None if not found.
        """
        try:
            import psycopg2
            import psycopg2.extras
            config = self._get_config()
            conn = psycopg2.connect(config.CONNECTION_STRING)

            base_filename = Path(filename).name
            name_without_ext = Path(base_filename).stem

            query = """
                SELECT
                    metadata->>'text' as text
                FROM vecs.documents
                WHERE metadata->>'file_name' = %s
                   OR metadata->>'file_name' = %s
                   OR metadata->>'file_name' LIKE %s
                ORDER BY (metadata->>'chunk_index')::int
            """

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, (filename, base_filename, f"{name_without_ext}.%"))
                chunks = cur.fetchall()

            conn.close()

            if not chunks:
                logger.warning(f"No text chunks found for document: {filename}")
                return None

            full_text = ' '.join([chunk['text'] for chunk in chunks if chunk['text']])
            logger.debug(f"📄 Retrieved {len(chunks)} chunks for {base_filename}, total length: {len(full_text)} chars")
            return full_text

        except Exception as e:
            logger.error(f"Failed to get document text for {filename}: {e}", exc_info=True)
            return None

    # ========================================================================
    # REGISTRY UPDATE
    # ========================================================================

    async def _update_registry_with_vrn(
        self,
        registry_id: str,
        vrn: Optional[str],
        make: Optional[str] = None,
        model: Optional[str] = None,
        extraction_method: str = 'none'
    ) -> bool:
        """
        Updates the document_registry with extracted data and sets the status.

        Args:
            registry_id: The UUID of the document registry entry.
            vrn: The extracted VRN (or None).
            make: The extracted vehicle make.
            model: The extracted vehicle model.
            extraction_method: The method used for extraction ('regex', 'ai', 'filename', or 'none').

        Returns:
            True if the update was successful, False otherwise.
        """
        try:
            import psycopg2
            import psycopg2.extras
            config = self._get_config()
            conn = psycopg2.connect(config.CONNECTION_STRING)

            if vrn:
                new_status = 'pending_assignment'
                extracted_data = {
                    'vrn': vrn,
                    'make': make,
                    'model': model,
                    'extraction_method': extraction_method
                }
                # Filter out null values
                extracted_data = {k: v for k, v in extracted_data.items() if v is not None}
                logger.info(f"✅ Setting status='pending_assignment' for registry {registry_id} with VRN={vrn}")
            else:
                new_status = 'unassigned'
                extracted_data = {'extraction_method': extraction_method}
                logger.info(f"⚠️ Setting status='unassigned' for registry {registry_id} (no VRN found)")

            query = """
                UPDATE vecs.document_registry
                SET
                    extracted_data = extracted_data || %s::jsonb,
                    status = %s
                WHERE id = %s
            """

            with conn.cursor() as cur:
                cur.execute(query, (json.dumps(extracted_data), new_status, registry_id))
                affected_rows = cur.rowcount
                conn.commit()

            conn.close()

            if affected_rows > 0:
                logger.debug(f"✅ Updated registry {registry_id}: status={new_status}, method={extraction_method}")
                return True
            else:
                logger.warning(f"Registry entry {registry_id} not found for update.")
                return False

        except Exception as e:
            logger.error(f"Failed to update registry {registry_id}: {e}", exc_info=True)
            return False

    # ========================================================================
    # BATCH PROCESSING
    # ========================================================================

    async def process_document(
        self,
        registry_id: str,
        filename: str,
        use_ai: bool = True
    ) -> Tuple[bool, Optional[str], str]:
        """
        Processes a single document to extract a VRN using a multi-step approach.

        Args:
            registry_id: The document registry UUID.
            filename: The document filename.
            use_ai: Flag to enable AI extraction as a fallback.

        Returns:
            A tuple containing (success_status, extracted_vrn, extraction_method).
        """
        logger.debug(f"🔍 Processing document: {filename}")

        # Step 1: Extract from filename
        vrn = self.extract_vrn_from_filename(filename)
        if vrn:
            await self._update_registry_with_vrn(registry_id, vrn, extraction_method='filename')
            return True, vrn, 'filename'

        # Step 2: Get document text for content-based extraction
        text = await self._get_document_text(filename)
        if not text:
            await self._update_registry_with_vrn(registry_id, None, extraction_method='no_text')
            return True, None, 'no_text'

        # Step 3: Extract from text using regex
        vrn = self.extract_vrn_from_text(text)
        if vrn:
            await self._update_registry_with_vrn(registry_id, vrn, extraction_method='regex')
            return True, vrn, 'regex'

        # Step 4: Fallback to AI if enabled
        if use_ai:
            ai_result = await self.extract_vrn_with_ai(text)
            if ai_result and ai_result.get('vrn'):
                await self._update_registry_with_vrn(
                    registry_id,
                    ai_result['vrn'],
                    make=ai_result.get('make'),
                    model=ai_result.get('model'),
                    extraction_method='ai'
                )
                return True, ai_result['vrn'], 'ai'

        # Step 5: No VRN found
        await self._update_registry_with_vrn(registry_id, None, extraction_method='none')
        return True, None, 'none'

    async def process_batch(
        self,
        document_ids: Optional[List[str]] = None,
        use_ai: bool = True
    ) -> Dict[str, Any]:
        """
        Processes a batch of documents to extract VRNs.

        Args:
            document_ids: A list of specific registry IDs to process.
                          If None, processes all documents with status='processed'.
            use_ai: Flag to enable AI extraction as a fallback.

        Returns:
            A dictionary with processing statistics.
        """
        stats = {
            'total_processed': 0, 'vrn_found': 0, 'vrn_not_found': 0, 'failed': 0,
            'extraction_methods': {'regex': 0, 'ai': 0, 'filename': 0, 'none': 0, 'no_text': 0}
        }

        try:
            import psycopg2
            import psycopg2.extras
            config = self._get_config()
            conn = psycopg2.connect(config.CONNECTION_STRING)

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if document_ids:
                    placeholders = ','.join(['%s'] * len(document_ids))
                    query = f"SELECT id, raw_file_path FROM vecs.document_registry WHERE id IN ({placeholders})"
                    cur.execute(query, document_ids)
                else:
                    query = "SELECT id, raw_file_path FROM vecs.document_registry WHERE status = 'processed' ORDER BY uploaded_at DESC"
                    cur.execute(query)
                documents = cur.fetchall()

            conn.close()

            logger.info(f"📋 Found {len(documents)} documents to process for VRN extraction.")

            for doc in documents:
                try:
                    success, vrn, method = await self.process_document(
                        str(doc['id']), doc['raw_file_path'], use_ai=use_ai
                    )
                    stats['total_processed'] += 1
                    if success:
                        if vrn:
                            stats['vrn_found'] += 1
                            logger.info(f"  ✅ {doc['raw_file_path']}: VRN={vrn} (method={method})")
                        else:
                            stats['vrn_not_found'] += 1
                            logger.info(f"  ⚠️ {doc['raw_file_path']}: No VRN found")
                        stats['extraction_methods'][method] += 1
                    else:
                        stats['failed'] += 1
                        logger.error(f"  ❌ {doc['raw_file_path']}: Processing failed")
                except Exception as e:
                    stats['failed'] += 1
                    logger.error(f"  ❌ Unhandled exception for {doc['raw_file_path']}: {e}", exc_info=True)


            logger.info(
                f"📊 VRN Extraction Complete: "
                f"{stats['vrn_found']} found, "
                f"{stats['vrn_not_found']} not found, "
                f"{stats['failed']} failed."
            )
            return stats

        except Exception as e:
            logger.error(f"Batch processing failed: {e}", exc_info=True)
            return stats


# Singleton instance
_vrn_extraction_service: Optional[VRNExtractionService] = None


def get_vrn_extraction_service() -> VRNExtractionService:
    """
    Returns a singleton instance of the VRNExtractionService.
    """
    global _vrn_extraction_service
    if _vrn_extraction_service is None:
        _vrn_extraction_service = VRNExtractionService()
    return _vrn_extraction_service