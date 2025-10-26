# query_processing/query_preprocessor.py
# Hybrid query preprocessing: Rule-based validation + AI enhancement
# Solves stop words problem ("the", "to") and improves complex queries

import logging
import re
from typing import Optional, List, Tuple
from dataclasses import dataclass
import google.generativeai as genai

logger = logging.getLogger(__name__)


# English stop words - common words with no search value
STOP_WORDS = {
    # Articles
    'a', 'an', 'the',

    # Prepositions
    'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'about',
    'into', 'through', 'during', 'before', 'after', 'above', 'below',
    'between', 'under', 'over',

    # Conjunctions
    'and', 'or', 'but', 'if', 'while', 'because', 'as', 'so', 'than',

    # Pronouns
    'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her',
    'us', 'them', 'my', 'your', 'his', 'its', 'our', 'their',

    # Verbs
    'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has',
    'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could',
    'may', 'might', 'must', 'can',

    # Common words
    'this', 'that', 'these', 'those', 'what', 'which', 'who', 'when',
    'where', 'why', 'how', 'all', 'each', 'every', 'some', 'any',
    'both', 'few', 'more', 'most', 'other', 'such', 'no', 'not',
    'only', 'own', 'same', 'too', 'very', 'just'
}

# Known acronyms in vehicle documentation domain
KNOWN_ACRONYMS = {
    'vrn': 'vehicle registration number',
    'nct': 'national car test',
    'cvrt': 'commercial vehicle roadworthiness test',
    'ncr': 'national car registry',
    'vin': 'vehicle identification number',
}


@dataclass
class PreprocessingResult:
    """Result of query preprocessing"""
    query: str  # Cleaned/enhanced query
    original_query: str  # Original user input
    method: str  # "rule_based", "ai_enhanced", or "rejected"
    removed_stop_words: List[str]  # Stop words that were removed
    is_valid: bool  # Whether query is valid for search
    rejection_reason: Optional[str] = None  # Why query was rejected
    ai_enhancement: Optional[str] = None  # AI enhancement details


class QueryPreprocessor:
    """
    Hybrid query preprocessor with rule-based and AI enhancement.

    Pipeline:
    1. Fast validation (length, empty check)
    2. Stop words removal (rule-based)
    3. AI enhancement (conditional, for complex queries)
    """

    def __init__(self, config, enable_ai_enhancement: bool = True):
        """
        Initialize query preprocessor

        Args:
            config: RAGConfig with LLM settings
            enable_ai_enhancement: Whether to use AI for complex queries
        """
        self.config = config
        self.enable_ai_enhancement = enable_ai_enhancement

        # Initialize Gemini for AI enhancement
        if enable_ai_enhancement:
            try:
                genai.configure(api_key=config.llm.api_key)
                self.ai_model = genai.GenerativeModel(config.llm.extraction_model)
                logger.info("[+] Query preprocessor initialized with AI enhancement")
            except Exception as e:
                logger.warning(f"[!] AI enhancement disabled: {e}")
                self.enable_ai_enhancement = False
        else:
            logger.info("[+] Query preprocessor initialized (rule-based only)")

    def preprocess(self, query: str) -> PreprocessingResult:
        """
        Main preprocessing pipeline

        Args:
            query: Raw user query

        Returns:
            PreprocessingResult with cleaned query or rejection
        """
        original_query = query

        # LEVEL 1: Fast validation
        validation_result = self._validate_query(query)
        if not validation_result[0]:
            return PreprocessingResult(
                query="",
                original_query=original_query,
                method="rejected",
                removed_stop_words=[],
                is_valid=False,
                rejection_reason=validation_result[1]
            )

        # SIMPLIFIED PREPROCESSING: Pass query as-is
        # QueryEngine (LlamaIndex) handles query understanding internally
        # No need for aggressive stop words removal

        # Just basic normalization
        cleaned_query = query.strip()

        # Return the query as-is for QueryEngine to handle
        return PreprocessingResult(
            query=cleaned_query,
            original_query=original_query,
            method="passthrough",  # Indicates minimal processing
            removed_stop_words=[],  # No stop words removed
            is_valid=True,
            ai_enhancement="Query passed to QueryEngine for natural language understanding"
        )

    def _validate_query(self, query: str) -> Tuple[bool, Optional[str]]:
        """
        Fast validation checks

        Returns:
            (is_valid, rejection_reason)
        """
        if not query or not query.strip():
            return False, "Query is empty"

        if len(query.strip()) < 2:
            return False, "Query is too short (minimum 2 characters)"

        # Check for only special characters
        if re.match(r'^[^a-zA-Z0-9]+$', query):
            return False, "Query contains only special characters"

        return True, None

    def _remove_stop_words(self, query: str) -> Tuple[str, List[str]]:
        """
        Remove stop words from query

        Returns:
            (cleaned_query, removed_words)
        """
        # Tokenize (simple split by whitespace)
        tokens = query.split()

        removed = []
        kept = []

        for token in tokens:
            # Clean token (remove punctuation for comparison)
            clean_token = re.sub(r'[^\w]', '', token.lower())

            if clean_token in STOP_WORDS:
                removed.append(token)
            else:
                kept.append(token)

        cleaned_query = ' '.join(kept)

        if removed:
            logger.debug(f"[*] Removed stop words: {removed}")

        return cleaned_query, removed

    def _should_use_ai_enhancement(self, query: str) -> bool:
        """
        Determine if query needs AI enhancement

        AI enhancement is useful for:
        - Single-word queries (ambiguous)
        - Queries with acronyms
        - Potential typos
        """
        tokens = query.lower().split()

        # Single word query - might be ambiguous
        if len(tokens) == 1:
            # Check if it's a known acronym
            if tokens[0] in KNOWN_ACRONYMS:
                return True

            # Very short query might benefit from expansion
            if len(tokens[0]) <= 4:
                return True

        # Check for known acronyms in query
        for token in tokens:
            if token.lower() in KNOWN_ACRONYMS:
                return True

        # Check for potential typos (very basic heuristic)
        # Words with repeated characters might be typos: "driveer", "vehiclee"
        for token in tokens:
            if len(token) > 3 and re.search(r'(.)\1{2,}', token):
                return True

        return False

    def _ai_enhance_query(self, query: str) -> str:
        """
        Use AI to enhance query

        Capabilities:
        - Acronym expansion
        - Typo correction
        - Query reformulation
        """
        prompt = f"""You are a search query optimizer for a vehicle documentation system.

User query: "{query}"

Your task:
1. If the query contains acronyms (VRN, NCT, CVRT, VIN), expand them
2. If there are obvious typos, correct them
3. Keep the query concise and search-friendly
4. Do NOT add stop words

Known acronyms:
- VRN = vehicle registration number
- NCT = national car test
- CVRT = commercial vehicle roadworthiness test
- VIN = vehicle identification number

Respond with ONLY the optimized query (no explanation):"""

        try:
            response = self.ai_model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.0,  # Deterministic
                    'max_output_tokens': 50,
                }
            )

            enhanced = response.text.strip()

            # Remove quotes if AI added them
            enhanced = enhanced.strip('"\'')

            # Validate AI output (should not be empty or drastically different)
            if enhanced and len(enhanced) > 0 and len(enhanced) < len(query) * 3:
                return enhanced
            else:
                logger.warning(f"[!] AI enhancement suspicious: '{enhanced}', using original")
                return query

        except Exception as e:
            logger.error(f"[!] AI enhancement error: {e}")
            return query


# Convenience functions for direct use

def validate_and_clean_query(query: str, config=None) -> PreprocessingResult:
    """
    Quick validation and cleaning without AI enhancement

    Use this for fast preprocessing when AI is not needed.
    """
    preprocessor = QueryPreprocessor(config, enable_ai_enhancement=False)
    return preprocessor.preprocess(query)


def preprocess_query_with_ai(query: str, config) -> PreprocessingResult:
    """
    Full preprocessing with AI enhancement

    Use this for best quality (slower, costs API calls).
    """
    preprocessor = QueryPreprocessor(config, enable_ai_enhancement=True)
    return preprocessor.preprocess(query)
