# query_processing/query_validator.py
# Professional Query Validation with LLM-based intent classification
# Validates if query is meaningful and relevant to the domain

import logging
from typing import Optional, Dict
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class QueryIntent(Enum):
    """Query intent classification"""
    VEHICLE_SEARCH = "vehicle_search"  # Searching for vehicle info
    PERSON_SEARCH = "person_search"    # Searching for person/driver
    DOCUMENT_SEARCH = "document_search"  # Searching for documents
    DATE_QUERY = "date_query"          # Date-related queries
    INVALID = "invalid"                # Not a valid query
    UNKNOWN = "unknown"                # Cannot determine intent


@dataclass
class QueryValidationResult:
    """Result of query validation"""
    is_valid: bool
    intent: QueryIntent
    confidence: float
    reason: str
    metadata: Dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class QueryValidator:
    """Professional query validator with LLM-based intent classification"""

    def __init__(self, config):
        self.config = config
        self.llm = None
        self._initialize_llm()

    def _initialize_llm(self):
        """Initialize LLM for query validation"""
        try:
            from llama_index.llms.google_genai import GoogleGenAI

            self.llm = GoogleGenAI(
                model=self.config.llm.extraction_model,
                api_key=self.config.llm.api_key,
                temperature=0.0,  # Deterministic
            )
            logger.info("✅ Query Validator initialized with Gemini")

        except Exception as e:
            logger.warning(f"⚠️ LLM not available for query validation: {e}")
            self.llm = None

    async def validate_query(self, query: str) -> QueryValidationResult:
        """
        Validate if query is meaningful and relevant to vehicle documentation domain

        Args:
            query: User's search query

        Returns:
            QueryValidationResult with validation status and intent
        """
        query = query.strip()

        # Basic validation: empty or too short
        if not query:
            return QueryValidationResult(
                is_valid=False,
                intent=QueryIntent.INVALID,
                confidence=1.0,
                reason="Empty query"
            )

        if len(query) < 2:
            return QueryValidationResult(
                is_valid=False,
                intent=QueryIntent.INVALID,
                confidence=1.0,
                reason="Query too short (< 2 characters)"
            )

        # Check if query is just a single common word
        single_word_stopwords = {
            'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or',
            'is', 'are', 'was', 'were', 'be', 'have', 'has', 'had', 'do', 'does'
        }
        if len(query.split()) == 1 and query.lower() in single_word_stopwords:
            return QueryValidationResult(
                is_valid=False,
                intent=QueryIntent.INVALID,
                confidence=0.95,
                reason="Query is a single stop word with no meaning"
            )

        # Use LLM for intent classification if available
        if self.llm:
            return await self._llm_validate(query)
        else:
            # Fallback to rule-based validation
            return await self._rule_based_validate(query)

    async def _llm_validate(self, query: str) -> QueryValidationResult:
        """LLM-based query validation and intent classification"""
        try:
            # Use validation prompt from config
            validation_prompt = self.config.domain.validation_prompt_template.format(query=query)

            # Add examples
            validation_prompt += """

Examples:
- "231-D-54321" → VALID: yes, INTENT: vehicle_search, CONFIDENCE: 0.95, REASON: VRN format
- "John Nolan" → VALID: yes, INTENT: person_search, CONFIDENCE: 0.90, REASON: Person name
- "FORD TRANSIT" → VALID: yes, INTENT: vehicle_search, CONFIDENCE: 0.85, REASON: Vehicle make/model
- "insurance documents" → VALID: yes, INTENT: document_search, CONFIDENCE: 0.90, REASON: Document type
- "the biggest river in USA" → VALID: no, INTENT: invalid, CONFIDENCE: 0.95, REASON: Not related to vehicles
- "a" → VALID: no, INTENT: invalid, CONFIDENCE: 1.0, REASON: Single meaningless character
- "asdfghjkl" → VALID: no, INTENT: invalid, CONFIDENCE: 0.98, REASON: Random gibberish

Your response:"""

            response = await self.llm.acomplete(
                validation_prompt,
                max_tokens=100
            )

            result_text = response.text.strip()
            return self._parse_llm_validation_response(result_text, query)

        except Exception as e:
            logger.warning(f"⚠️ LLM validation failed: {e}")
            # Fallback to rule-based
            return await self._rule_based_validate(query)

    def _parse_llm_validation_response(self, response: str, query: str) -> QueryValidationResult:
        """Parse LLM validation response"""
        try:
            lines = [line.strip() for line in response.split('\n') if line.strip()]

            is_valid = False
            intent = QueryIntent.UNKNOWN
            confidence = 0.5
            reason = "LLM validation completed"

            for line in lines:
                if line.startswith("VALID:"):
                    is_valid = "yes" in line.lower()
                elif line.startswith("INTENT:"):
                    intent_str = line.split(":", 1)[1].strip().lower()
                    try:
                        intent = QueryIntent(intent_str)
                    except ValueError:
                        intent = QueryIntent.UNKNOWN
                elif line.startswith("CONFIDENCE:"):
                    try:
                        confidence = float(line.split(":", 1)[1].strip())
                    except:
                        confidence = 0.5
                elif line.startswith("REASON:"):
                    reason = line.split(":", 1)[1].strip()

            return QueryValidationResult(
                is_valid=is_valid,
                intent=intent,
                confidence=confidence,
                reason=reason,
                metadata={"method": "llm", "raw_response": response}
            )

        except Exception as e:
            logger.warning(f"⚠️ Failed to parse LLM response: {e}")
            # If parsing fails, assume valid to avoid blocking
            return QueryValidationResult(
                is_valid=True,
                intent=QueryIntent.UNKNOWN,
                confidence=0.3,
                reason=f"Parse error: {str(e)}",
                metadata={"method": "llm_fallback", "error": str(e)}
            )

    async def _rule_based_validate(self, query: str) -> QueryValidationResult:
        """Rule-based fallback validation"""
        query_lower = query.lower()
        words = query_lower.split()

        # Vehicle-related keywords
        vehicle_keywords = {
            'vehicle', 'car', 'van', 'truck', 'ford', 'toyota', 'honda',
            'transit', 'corolla', 'civic', 'registration', 'vrn', 'vin',
            'make', 'model', 'year', 'colour', 'color'
        }

        # Person-related keywords
        person_keywords = {
            'driver', 'owner', 'person', 'name', 'john', 'mary', 'michael'
        }

        # Document-related keywords
        document_keywords = {
            'insurance', 'nct', 'certificate', 'document', 'record', 'cert',
            'policy', 'test', 'inspection', 'tax', 'disc',
            'service', 'maintenance', 'repair', 'fuel', 'toll', 'receipt'
        }

        # Date-related keywords
        date_keywords = {
            'expiry', 'expire', 'date', 'when', 'renewal', 'valid', 'until'
        }

        # Check for VRN pattern (e.g., 231-D-54321)
        import re
        vrn_pattern = r'\d{2,3}-[A-Z]-\d{4,5}'
        if re.search(vrn_pattern, query):
            return QueryValidationResult(
                is_valid=True,
                intent=QueryIntent.VEHICLE_SEARCH,
                confidence=0.95,
                reason="Matches VRN pattern",
                metadata={"method": "rule_based", "pattern": "vrn"}
            )

        # Check for capitalized names (e.g., "John Nolan")
        name_pattern = r'\b[A-Z][a-z]+(?: [A-Z][a-z]+)+\b'
        if re.search(name_pattern, query):
            return QueryValidationResult(
                is_valid=True,
                intent=QueryIntent.PERSON_SEARCH,
                confidence=0.85,
                reason="Matches person name pattern",
                metadata={"method": "rule_based", "pattern": "name"}
            )

        # Check keyword matches
        query_words = set(words)

        if query_words & vehicle_keywords:
            return QueryValidationResult(
                is_valid=True,
                intent=QueryIntent.VEHICLE_SEARCH,
                confidence=0.75,
                reason="Contains vehicle-related keywords"
            )

        if query_words & person_keywords:
            return QueryValidationResult(
                is_valid=True,
                intent=QueryIntent.PERSON_SEARCH,
                confidence=0.75,
                reason="Contains person-related keywords"
            )

        if query_words & document_keywords:
            return QueryValidationResult(
                is_valid=True,
                intent=QueryIntent.DOCUMENT_SEARCH,
                confidence=0.75,
                reason="Contains document-related keywords"
            )

        if query_words & date_keywords:
            return QueryValidationResult(
                is_valid=True,
                intent=QueryIntent.DATE_QUERY,
                confidence=0.70,
                reason="Contains date-related keywords"
            )

        # If query has reasonable length and structure, assume valid but unknown intent
        if len(words) >= 2 and len(query) >= 5:
            return QueryValidationResult(
                is_valid=True,
                intent=QueryIntent.UNKNOWN,
                confidence=0.50,
                reason="Query seems meaningful but intent unclear",
                metadata={"method": "rule_based"}
            )

        # Default: invalid
        return QueryValidationResult(
            is_valid=False,
            intent=QueryIntent.INVALID,
            confidence=0.80,
            reason="Does not match any known patterns or keywords",
            metadata={"method": "rule_based"}
        )
