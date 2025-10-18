# query_processing/query_rewriter.py
# Advanced query rewriting with full async support
# UPDATED: Async methods for FastAPI compatibility

import re
import logging
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

@dataclass
class QueryRewriteResult:
    """Result of query rewriting"""
    original_query: str
    rewrites: List[str]
    method: str
    confidence: float
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class BaseQueryRewriter(ABC):
    """Base class for query rewriters"""
    
    @abstractmethod
    async def rewrite(self, query: str, num_rewrites: int = 3) -> QueryRewriteResult:
        """Rewrite query into multiple variations - NOW ASYNC"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if rewriter is available"""
        pass

class LLMQueryRewriter(BaseQueryRewriter):
    """LLM-based query rewriting with async support"""
    
    def __init__(self, llm_config):
        self.llm_config = llm_config
        self.llm = None
        self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize LLM for query rewriting"""
        try:
            from llama_index.llms.google_genai import GoogleGenAI
            
            self.llm = GoogleGenAI(
                model=self.llm_config.rewrite_model,
                api_key=self.llm_config.api_key,
                temperature=self.llm_config.rewrite_temperature,
                max_tokens=self.llm_config.rewrite_max_tokens,
            )
            logger.info(f"✅ LLM Query Rewriter initialized with Gemini: {self.llm_config.rewrite_model}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize LLM Query Rewriter with Gemini: {e}")
            self.llm = None
    
    def is_available(self) -> bool:
        """Check if LLM is available"""
        return self.llm is not None
    
    async def rewrite(self, query: str, num_rewrites: int = 3) -> QueryRewriteResult:
        """Rewrite query using LLM - ASYNC"""
        if not self.is_available():
            return QueryRewriteResult(
                original_query=query,
                rewrites=[query],
                method="llm_unavailable",
                confidence=0.0
            )
        
        try:
            rewrites = await self._expand_query(query, num_rewrites)
            
            if not rewrites:
                rewrites = await self._simplify_query(query)
            
            unique_rewrites = self._filter_rewrites(rewrites, query)
            
            logger.info(f"🔄 LLM generated {len(unique_rewrites)} query rewrites")
            
            return QueryRewriteResult(
                original_query=query,
                rewrites=unique_rewrites,
                method="llm_expand",
                confidence=0.8,
                metadata={
                    "total_generated": len(rewrites),
                    "after_filtering": len(unique_rewrites),
                    "model": self.llm_config.rewrite_model
                }
            )
            
        except Exception as e:
            logger.warning(f"⚠️ LLM query rewriting failed: {e}")
            return QueryRewriteResult(
                original_query=query,
                rewrites=[query],
                method="llm_error",
                confidence=0.0,
                metadata={"error": str(e)}
            )
    
    async def _expand_query(self, query: str, num_rewrites: int) -> List[str]:
        """Expand query into multiple variations - ASYNC"""
        from config.settings import config
        
        prompt = config.query_rewrite.expand_query_prompt.format(
            query=query, 
            num_queries=num_rewrites
        )
        
        # FIXED: Use async method
        response = await self.llm.acomplete(prompt)
        rewrites = self._parse_llm_response(response.text)
        return rewrites
    
    async def _simplify_query(self, query: str) -> List[str]:
        """Simplify complex query - ASYNC"""
        from config.settings import config
        
        prompt = config.query_rewrite.simplify_query_prompt.format(query=query)
        
        # FIXED: Use async method
        response = await self.llm.acomplete(prompt)
        simplified = response.text.strip()
        
        if simplified and simplified != query:
            return [simplified]
        return []
    
    def _parse_llm_response(self, response: str) -> List[str]:
        """Parse LLM response to extract queries"""
        rewrites = []
        lines = response.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            
            if not line or line.lower().startswith(('generate', 'search', 'queries', 'variations')):
                continue
            
            cleaned = re.sub(r'^\d+[\.\)]\s*', '', line)
            cleaned = re.sub(r'^[-•*]\s*', '', cleaned)
            cleaned = cleaned.strip('"\'')
            
            if cleaned and len(cleaned.split()) >= 2:
                rewrites.append(cleaned)
        
        return rewrites
    
    def _filter_rewrites(self, rewrites: List[str], original: str) -> List[str]:
        """Filter and deduplicate rewrites"""
        if not rewrites:
            return [original]
        
        unique_rewrites = []
        seen = set()
        original_lower = original.lower()
        
        for rewrite in rewrites:
            rewrite_clean = rewrite.strip()
            rewrite_lower = rewrite_clean.lower()
            
            if (not rewrite_clean or 
                rewrite_lower in seen or 
                rewrite_lower == original_lower):
                continue
            
            if self._similarity_too_high(rewrite_lower, original_lower):
                continue
            
            seen.add(rewrite_lower)
            unique_rewrites.append(rewrite_clean)
        
        if original not in unique_rewrites:
            unique_rewrites.insert(0, original)
        
        return unique_rewrites[:5]
    
    def _similarity_too_high(self, text1: str, text2: str, threshold: float = 0.8) -> bool:
        """Check if two texts are too similar"""
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return False
        
        overlap = len(words1.intersection(words2))
        similarity = overlap / min(len(words1), len(words2))
        
        return similarity > threshold

class RuleBasedQueryRewriter(BaseQueryRewriter):
    """Rule-based query rewriting - synchronous, wrapped in async"""
    
    def __init__(self):
        self.question_patterns = {
            r"tell me about (.+)": ["{}",  "information about {}", "details about {}"],
            r"who is (.+)": ["{}", "{} biography", "{} information"],
            r"show me (.+)": ["{}", "find {}", "{} documents"],
            r"find (?:information )?(?:about )?(.+)": ["{}", "{} info", "{} details"],
            r"what (?:about|is) (.+)": ["{}", "{} information", "about {}"],
            r"give me (.+)": ["{}", "provide {}", "{} information"]
        }
        
        self.expansion_templates = [
            "{} information",
            "{} details",
            "{} documents", 
            "{} training",
            "{} certifications",
            "about {}",
            "find {}",
            "{} profile"
        ]
    
    def is_available(self) -> bool:
        """Rule-based rewriter is always available"""
        return True
    
    async def rewrite(self, query: str, num_rewrites: int = 3) -> QueryRewriteResult:
        """Rewrite query using rules - ASYNC WRAPPER"""
        query = query.strip()
        rewrites = []
        method_used = "rules"
        
        pattern_rewrites = self._apply_patterns(query)
        if pattern_rewrites:
            rewrites.extend(pattern_rewrites)
            method_used = "pattern_based"
        
        if len(rewrites) < num_rewrites:
            expansion_rewrites = self._expand_with_templates(query, num_rewrites - len(rewrites))
            rewrites.extend(expansion_rewrites)
            if not pattern_rewrites:
                method_used = "template_expansion"
            else:
                method_used = "pattern_and_template"
        
        unique_rewrites = self._deduplicate_rewrites(rewrites, query)
        confidence = 0.6 if pattern_rewrites else 0.4
        
        logger.info(f"🔧 Rule-based generated {len(unique_rewrites)} query rewrites")
        
        return QueryRewriteResult(
            original_query=query,
            rewrites=unique_rewrites,
            method=method_used,
            confidence=confidence,
            metadata={
                "patterns_matched": len(pattern_rewrites) if pattern_rewrites else 0,
                "templates_used": len(expansion_rewrites) if 'expansion_rewrites' in locals() else 0
            }
        )
    
    def _apply_patterns(self, query: str) -> List[str]:
        """Apply question patterns to rewrite query"""
        rewrites = []
        query_lower = query.lower()
        
        for pattern, templates in self.question_patterns.items():
            match = re.search(pattern, query_lower, re.IGNORECASE)
            if match:
                entity = match.group(1).strip()
                
                for template in templates:
                    rewrite = template.format(entity)
                    if rewrite and rewrite != query.lower():
                        rewrites.append(rewrite)
                break
        
        return rewrites
    
    def _expand_with_templates(self, query: str, num_needed: int) -> List[str]:
        """Expand query using templates"""
        core_entity = self._extract_core_entity(query)
        if not core_entity:
            return []
        
        rewrites = []
        for template in self.expansion_templates:
            if len(rewrites) >= num_needed:
                break
                
            rewrite = template.format(core_entity)
            if rewrite != query.lower():
                rewrites.append(rewrite)
        
        return rewrites
    
    def _extract_core_entity(self, query: str) -> Optional[str]:
        """Extract core entity from query"""
        stop_words = {'tell', 'me', 'about', 'who', 'is', 'show', 'find', 'what', 'give', 'the', 'a', 'an'}
        words = [word for word in query.lower().split() if word not in stop_words]
        
        if words:
            return ' '.join(words)
        return None
    
    def _deduplicate_rewrites(self, rewrites: List[str], original: str) -> List[str]:
        """Remove duplicates and similar rewrites"""
        if not rewrites:
            return [original]
        
        unique_rewrites = []
        seen = set()
        original_lower = original.lower()
        
        for rewrite in rewrites:
            rewrite_clean = rewrite.strip()
            rewrite_lower = rewrite_clean.lower()
            
            if (rewrite_lower not in seen and 
                rewrite_lower != original_lower and
                len(rewrite_clean) > 2):
                
                seen.add(rewrite_lower)
                unique_rewrites.append(rewrite_clean)
        
        if original not in unique_rewrites:
            unique_rewrites.insert(0, original)
        
        return unique_rewrites

class HybridQueryRewriter(BaseQueryRewriter):
    """Hybrid rewriter combining multiple strategies - ASYNC"""
    
    def __init__(self, config):
        self.config = config
        self.rewriters = {}
        self._initialize_rewriters()
    
    def _initialize_rewriters(self):
        """Initialize available rewriters"""
        self.rewriters["rules"] = RuleBasedQueryRewriter()
        
        if self.config.query_rewrite.enabled:
            llm_rewriter = LLMQueryRewriter(self.config.llm)
            if llm_rewriter.is_available():
                self.rewriters["llm"] = llm_rewriter
        
        logger.info(f"🔧 Initialized query rewriters: {list(self.rewriters.keys())}")
    
    def is_available(self) -> bool:
        """Hybrid rewriter is available if any rewriter is available"""
        return len(self.rewriters) > 0
    
    async def rewrite(self, query: str, num_rewrites: int = 3) -> QueryRewriteResult:
        """Rewrite using hybrid approach - FULLY ASYNC"""
        all_rewrites = []
        methods_used = []
        total_confidence = 0.0
        
        if "llm" in self.rewriters:
            try:
                llm_result = await self.rewriters["llm"].rewrite(query, num_rewrites)
                all_rewrites.extend(llm_result.rewrites)
                methods_used.append("llm")
                total_confidence += llm_result.confidence * 0.7
            except Exception as e:
                logger.warning(f"⚠️ LLM rewriting failed: {e}")
        
        if "rules" in self.rewriters:
            try:
                rules_result = await self.rewriters["rules"].rewrite(query, num_rewrites)
                all_rewrites.extend(rules_result.rewrites)
                methods_used.append("rules")
                total_confidence += rules_result.confidence * 0.3
            except Exception as e:
                logger.warning(f"⚠️ Rule-based rewriting failed: {e}")
        
        unique_rewrites = self._combine_rewrites(all_rewrites, query, num_rewrites)
        final_confidence = min(1.0, total_confidence)
        
        logger.info(f"🔄 Hybrid rewriter generated {len(unique_rewrites)} queries using: {', '.join(methods_used)}")
        
        return QueryRewriteResult(
            original_query=query,
            rewrites=unique_rewrites,
            method="hybrid_" + "_".join(methods_used),
            confidence=final_confidence,
            metadata={
                "methods_used": methods_used,
                "total_candidates": len(all_rewrites),
                "final_count": len(unique_rewrites)
            }
        )
    
    def _combine_rewrites(self, all_rewrites: List[str], original: str, max_count: int) -> List[str]:
        """Combine rewrites from multiple sources"""
        unique_rewrites = []
        seen = set()
        original_lower = original.lower()
        
        unique_rewrites.append(original)
        seen.add(original_lower)
        
        for rewrite in all_rewrites:
            rewrite_clean = rewrite.strip()
            rewrite_lower = rewrite_clean.lower()
            
            if (rewrite_lower not in seen and 
                len(rewrite_clean) > 2 and
                len(unique_rewrites) < max_count + 1):
                
                seen.add(rewrite_lower)
                unique_rewrites.append(rewrite_clean)
        
        return unique_rewrites

class ProductionQueryRewriter:
    """Production-ready query rewriter with full async support"""
    
    def __init__(self, config):
        self.config = config
        self.rewriter = HybridQueryRewriter(config)
    
    async def rewrite_query(self, query: str, extracted_entity: Optional[str] = None) -> QueryRewriteResult:
        """Main entry point for query rewriting - FULLY ASYNC"""
        if not self.config.query_rewrite.enabled:
            return QueryRewriteResult(
                original_query=query,
                rewrites=[query],
                method="disabled",
                confidence=1.0
            )
        
        num_rewrites = self._determine_rewrite_count(query, extracted_entity)
        result = await self.rewriter.rewrite(query, num_rewrites)
        
        if extracted_entity and extracted_entity.strip() != query.strip():
            if extracted_entity not in result.rewrites:
                result.rewrites.insert(1, extracted_entity)
        
        logger.info(f"🔄 Final query variants ({len(result.rewrites)}): {result.rewrites}")
        
        return result
    
    def _determine_rewrite_count(self, query: str, extracted_entity: Optional[str] = None) -> int:
        """Determine optimal number of rewrites"""
        base_count = self.config.query_rewrite.max_rewrites
        
        if len(query.split()) <= 2:
            return max(1, base_count - 1)
        
        if len(query.split()) >= 6:
            return base_count
        
        return base_count - 1
    
    def get_rewriter_status(self) -> Dict[str, bool]:
        """Get status of all rewriters"""
        if hasattr(self.rewriter, 'rewriters'):
            return {name: rewriter.is_available() 
                   for name, rewriter in self.rewriter.rewriters.items()}
        return {"hybrid": self.rewriter.is_available()}