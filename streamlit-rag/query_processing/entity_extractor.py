# query_processing/entity_extractor.py
# Smart entity extraction with multiple methods and fallbacks
# UPDATED: Full async support for FastAPI compatibility

import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

@dataclass
class EntityExtractionResult:
    """Result of entity extraction"""
    entity: str
    confidence: float
    method: str
    alternatives: List[str] = None
    metadata: Dict = None
    
    def __post_init__(self):
        if self.alternatives is None:
            self.alternatives = []
        if self.metadata is None:
            self.metadata = {}

class BaseEntityExtractor(ABC):
    """Base class for entity extractors"""
    
    @abstractmethod
    async def extract(self, query: str) -> EntityExtractionResult:
        """Extract entity from query - NOW ASYNC"""
        pass
    
    @abstractmethod  
    def is_available(self) -> bool:
        """Check if extractor is available"""
        pass

class LLMEntityExtractor(BaseEntityExtractor):
    """LLM-based entity extraction with async support"""
    
    def __init__(self, llm_config):
        self.llm_config = llm_config
        self.llm = None
        self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize LLM for extraction"""
        try:
            from llama_index.llms.google_genai import GoogleGenAI
            
            self.llm = GoogleGenAI(
                model=self.llm_config.extraction_model,
                api_key=self.llm_config.api_key,
                temperature=self.llm_config.extraction_temperature,
                max_tokens=self.llm_config.extraction_max_tokens,
            )
            logger.info(f"✅ LLM Entity Extractor initialized with Gemini: {self.llm_config.extraction_model}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize LLM Entity Extractor with Gemini: {e}")
            self.llm = None
    
    def is_available(self) -> bool:
        """Check if LLM is available"""
        return self.llm is not None
    
    async def extract(self, query: str) -> EntityExtractionResult:
        """Extract entity using LLM - ASYNC"""
        if not self.is_available():
            return EntityExtractionResult(
                entity=query,
                confidence=0.0,
                method="llm_unavailable"
            )
        
        try:
            from config.settings import config
            extraction_prompt = config.entity_extraction.person_extraction_prompt.format(query=query)
            
            # FIXED: Use async method
            response = await self.llm.acomplete(extraction_prompt)
            extracted_entity = response.text.strip()
            
            # Clean extraction
            extracted_entity = self._clean_extraction(extracted_entity)
            
            # Validate extraction
            confidence = self._calculate_confidence(extracted_entity, query)
            
            if confidence > 0.5:
                logger.info(f"🎯 LLM extracted entity: '{extracted_entity}' (confidence: {confidence:.2f})")
                
                return EntityExtractionResult(
                    entity=extracted_entity,
                    confidence=confidence,
                    method="llm",
                    metadata={
                        "original_response": response.text,
                        "cleaned": True,
                        "model": self.llm_config.extraction_model
                    }
                )
            else:
                return EntityExtractionResult(
                    entity=query,
                    confidence=confidence,
                    method="llm_low_confidence",
                    metadata={"reason": "Low confidence extraction"}
                )
                
        except Exception as e:
            logger.warning(f"⚠️ LLM entity extraction failed: {e}")
            return EntityExtractionResult(
                entity=query,
                confidence=0.0,
                method="llm_error",
                metadata={"error": str(e)}
            )
    
    def _clean_extraction(self, extracted_entity: str) -> str:
        """Clean extracted entity"""
        cleaned = re.sub(r'^(name|answer|result)[:=]\s*', '', extracted_entity, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s*(is|the|answer|result)$', '', cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.strip('"\'')
        cleaned = ' '.join(cleaned.split())
        return cleaned
    
    def _calculate_confidence(self, entity: str, original_query: str) -> float:
        """Calculate confidence in extraction"""
        if not entity or len(entity.strip()) < 2:
            return 0.0
        
        question_words = {'question', 'query', 'extract', 'name', 'tell', 'about', 'who', 'is', 'find', 'show'}
        entity_words = set(entity.lower().split())
        
        if entity_words.intersection(question_words):
            return 0.2
        
        if len(entity) > len(original_query):
            return 0.1
        
        if re.match(r'^[A-Z][a-z]+(?: [A-Z][a-z]+)*$', entity):
            return 0.9
        
        if len(entity.split()) <= 3:
            return 0.7
        
        return 0.5

class RegexEntityExtractor(BaseEntityExtractor):
    """Regex-based entity extraction - synchronous, wrapped in async"""
    
    def __init__(self):
        self.patterns = [
            (r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', 0.8),
            (r'\b[A-Z][a-z]+\b', 0.6),
            (r'(?:about|is|find|show)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', 0.7),
        ]
        self.question_words = {'Tell', 'Show', 'Find', 'What', 'Who', 'Where', 'When', 'Why', 'How'}
    
    def is_available(self) -> bool:
        """Regex is always available"""
        return True
    
    async def extract(self, query: str) -> EntityExtractionResult:
        """Extract entity using regex patterns - ASYNC WRAPPER"""
        best_entity = None
        best_confidence = 0.0
        all_candidates = []
        
        for pattern, base_confidence in self.patterns:
            matches = re.findall(pattern, query)
            
            for match in matches:
                if match not in self.question_words:
                    confidence = self._calculate_regex_confidence(match, query, base_confidence)
                    all_candidates.append((match, confidence))
                    
                    if confidence > best_confidence:
                        best_entity = match
                        best_confidence = confidence
        
        if best_entity:
            alternatives = [candidate for candidate, conf in all_candidates 
                          if candidate != best_entity and conf > 0.5]
            
            logger.info(f"🎯 Regex extracted entity: '{best_entity}' (confidence: {best_confidence:.2f})")
            
            return EntityExtractionResult(
                entity=best_entity,
                confidence=best_confidence,
                method="regex",
                alternatives=alternatives,
                metadata={
                    "all_candidates": all_candidates,
                    "patterns_matched": len([m for p, _ in self.patterns for m in re.findall(p, query)])
                }
            )
        else:
            return EntityExtractionResult(
                entity=query.strip(),
                confidence=0.3,
                method="regex_fallback",
                metadata={"reason": "No regex patterns matched"}
            )
    
    def _calculate_regex_confidence(self, entity: str, query: str, base_confidence: float) -> float:
        """Calculate confidence for regex extraction"""
        confidence = base_confidence
        
        if len(entity.split()) > 1:
            confidence += 0.1
        
        if len(entity) > len(query) * 0.8:
            confidence -= 0.2
        
        entity_position = query.lower().find(entity.lower())
        if entity_position >= 0:
            position_factor = 1.0 - (entity_position / len(query))
            confidence += position_factor * 0.1
        
        return min(1.0, max(0.0, confidence))

class SpacyEntityExtractor(BaseEntityExtractor):
    """SpaCy-based entity extraction - synchronous, wrapped in async"""
    
    def __init__(self):
        self.nlp = None
        self._initialize_spacy()
    
    def _initialize_spacy(self):
        """Initialize SpaCy (if available)"""
        try:
            import spacy
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("✅ SpaCy Entity Extractor initialized")
        except (ImportError, OSError) as e:
            logger.warning(f"⚠️ SpaCy not available: {e}")
            self.nlp = None
    
    def is_available(self) -> bool:
        """Check if SpaCy is available"""
        return self.nlp is not None
    
    async def extract(self, query: str) -> EntityExtractionResult:
        """Extract entity using SpaCy NER - ASYNC WRAPPER"""
        if not self.is_available():
            return EntityExtractionResult(
                entity=query,
                confidence=0.0,
                method="spacy_unavailable"
            )
        
        try:
            doc = self.nlp(query)
            person_entities = [ent for ent in doc.ents if ent.label_ == "PERSON"]
            
            if person_entities:
                best_entity = person_entities[0]
                confidence = 0.8
                alternatives = [ent.text for ent in person_entities[1:]]
                
                logger.info(f"🎯 SpaCy extracted entity: '{best_entity.text}' (confidence: {confidence:.2f})")
                
                return EntityExtractionResult(
                    entity=best_entity.text,
                    confidence=confidence,
                    method="spacy",
                    alternatives=alternatives,
                    metadata={
                        "label": best_entity.label_,
                        "start": best_entity.start,
                        "end": best_entity.end,
                        "all_entities": [(ent.text, ent.label_) for ent in doc.ents]
                    }
                )
            else:
                return EntityExtractionResult(
                    entity=query.strip(),
                    confidence=0.2,
                    method="spacy_no_entities",
                    metadata={"entities_found": [(ent.text, ent.label_) for ent in doc.ents]}
                )
                
        except Exception as e:
            logger.warning(f"⚠️ SpaCy entity extraction failed: {e}")
            return EntityExtractionResult(
                entity=query,
                confidence=0.0,
                method="spacy_error",
                metadata={"error": str(e)}
            )

class ProductionEntityExtractor:
    """Production-ready entity extractor with full async support"""
    
    def __init__(self, config):
        self.config = config
        self.extractors = {}
        self._initialize_extractors()
    
    def _initialize_extractors(self):
        """Initialize available extractors"""
        self.extractors["regex"] = RegexEntityExtractor()
        
        if "llm" in self.config.entity_extraction.extraction_methods:
            llm_extractor = LLMEntityExtractor(self.config.llm)
            if llm_extractor.is_available():
                self.extractors["llm"] = llm_extractor
        
        if "spacy" in self.config.entity_extraction.extraction_methods:
            spacy_extractor = SpacyEntityExtractor()
            if spacy_extractor.is_available():
                self.extractors["spacy"] = spacy_extractor
        
        logger.info(f"🔧 Initialized entity extractors: {list(self.extractors.keys())}")
    
    async def extract_entity(self, query: str) -> EntityExtractionResult:
        """Extract entity using multiple methods - FULLY ASYNC"""
        if not query or not query.strip():
            return EntityExtractionResult(
                entity="",
                confidence=0.0,
                method="empty_query"
            )
        
        query = query.strip()
        extraction_order = ["llm", "spacy", "regex"]
        results = []
        
        for extractor_name in extraction_order:
            if extractor_name in self.extractors:
                try:
                    result = await self.extractors[extractor_name].extract(query)
                    results.append(result)
                    
                    if result.confidence > 0.7:
                        logger.info(f"✅ High confidence extraction: '{result.entity}' via {result.method}")
                        return result
                        
                except Exception as e:
                    logger.warning(f"⚠️ Extractor {extractor_name} failed: {e}")
                    continue
        
        if results:
            best_result = max(results, key=lambda x: x.confidence)
            best_result.metadata["all_attempts"] = [
                {"method": r.method, "entity": r.entity, "confidence": r.confidence} 
                for r in results
            ]
            logger.info(f"🎯 Best extraction: '{best_result.entity}' via {best_result.method} (confidence: {best_result.confidence:.2f})")
            return best_result
        
        return EntityExtractionResult(
            entity=query,
            confidence=0.1,
            method="fallback",
            metadata={"reason": "All extractors failed"}
        )
    
    async def get_extraction_variants(self, query: str) -> List[str]:
        """Get multiple extraction variants - ASYNC"""
        base_result = await self.extract_entity(query)
        variants = [base_result.entity]
        
        if base_result.alternatives:
            variants.extend(base_result.alternatives[:2])
        
        if query.strip() not in variants:
            variants.append(query.strip())
        
        unique_variants = []
        for variant in variants:
            if variant not in unique_variants:
                unique_variants.append(variant)
        
        logger.info(f"🔧 Generated {len(unique_variants)} extraction variants: {unique_variants}")
        return unique_variants
    
    def validate_entity(self, entity: str, original_query: str) -> Tuple[bool, float]:
        """Validate extracted entity"""
        if not entity or len(entity.strip()) < 2:
            return False, 0.0
        
        entity_lower = entity.lower()
        if entity_lower in self.config.entity_extraction.known_entities:
            return True, 0.95
        
        question_words = {'question', 'query', 'extract', 'name', 'tell', 'about', 'who', 'is', 'find', 'show'}
        entity_words = set(entity.lower().split())
        
        if entity_words.intersection(question_words):
            return False, 0.1
        
        if len(entity) > len(original_query):
            return False, 0.1
        
        return True, 0.6
    
    def get_available_extractors(self) -> List[str]:
        """Get list of available extractors"""
        return list(self.extractors.keys())
    
    def get_extractor_status(self) -> Dict[str, bool]:
        """Get status of all extractors"""
        return {name: extractor.is_available() for name, extractor in self.extractors.items()}