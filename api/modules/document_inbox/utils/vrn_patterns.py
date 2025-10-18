#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# api/modules/document_inbox/utils/vrn_patterns.py
# Irish Vehicle Registration Number (VRN) patterns and extraction utilities

import re
import logging
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)


class VRNPatterns:
    """
    Irish Vehicle Registration Number (VRN) pattern recognition and extraction.
    
    Irish VRN formats:
    - New format (2013+): YYY-C-NNNNN (e.g., 191-D-12345, 241-KY-999)
    - Old format (1987-2012): YY-C-NNNNN (e.g., 06-D-12345, 99-KY-1234)
    
    Where:
    - YYY/YY = Year (191 = 2019 first half, 192 = 2019 second half)
    - C = County code (D=Dublin, KY=Kerry, G=Galway, etc.)
    - NNNNN = Sequential number
    """
    
    # Irish VRN Regex Patterns (ordered by specificity)
    PATTERNS = [
        # New format (2013+): YYY-CC-NNNNN (two-letter county codes)
        (r'\b\d{3}-[A-Z]{2}-\d{1,6}\b', 'new_format_two_letter'),
        
        # New format (2013+): YYY-C-NNNNN (single-letter county codes)
        (r'\b\d{3}-[A-Z]-\d{1,6}\b', 'new_format_single_letter'),
        
        # Old format (1987-2012): YY-CC-NNNNN (two-letter county codes)
        (r'\b\d{2}-[A-Z]{2}-\d{1,6}\b', 'old_format_two_letter'),
        
        # Old format (1987-2012): YY-C-NNNNN (single-letter county codes)
        (r'\b\d{2}-[A-Z]-\d{1,6}\b', 'old_format_single_letter'),
        
        # Without hyphens: YYYC[C]NNNNN (less common, but possible)
        (r'\b\d{3}[A-Z]{1,2}\d{1,6}\b', 'no_hyphens_new'),
        (r'\b\d{2}[A-Z]{1,2}\d{1,6}\b', 'no_hyphens_old'),
    ]
    
    # Compile patterns for performance
    COMPILED_PATTERNS = [(re.compile(pattern, re.IGNORECASE), name) for pattern, name in PATTERNS]
    
    # Valid Irish county codes (for validation)
    VALID_COUNTY_CODES = {
        # Single letter codes
        'C', 'CE', 'CN', 'CW', 'D', 'DL', 'G', 'KE', 'KK', 'KY',
        'L', 'LD', 'LH', 'LK', 'LM', 'LS', 'MH', 'MN', 'MO', 'OY',
        'RN', 'SO', 'T', 'TS', 'W', 'WH', 'WW', 'WX',
        # Full county names (sometimes appear in documents)
        'DUBLIN', 'CORK', 'GALWAY', 'KERRY', 'LIMERICK', 'WATERFORD'
    }
    
    # Common false positives to filter out
    FALSE_POSITIVES = [
        # Date patterns that might match VRN regex
        r'\d{2}-\d{2}-\d{4}',  # DD-MM-YYYY
        r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
        # Phone numbers
        r'\d{3}-\d{3}-\d{4}',  # Phone format
        # Other patterns
        r'\d+-[A-Z]+-\d+[A-Z]',  # Mixed alpha-numeric codes
    ]
    
    COMPILED_FALSE_POSITIVES = [re.compile(pattern, re.IGNORECASE) for pattern in FALSE_POSITIVES]
    
    
    def extract_vrn(self, text: str) -> Optional[str]:
        """
        Extract Vehicle Registration Number from text using regex patterns.
        
        Args:
            text: Text to search for VRN
            
        Returns:
            VRN string if found, None otherwise
        """
        if not text or len(text.strip()) < 5:
            return None
        
        candidates = []
        
        # Try each pattern
        for pattern, pattern_name in self.COMPILED_PATTERNS:
            matches = pattern.findall(text)
            
            if matches:
                for match in matches:
                    # Validate the match
                    if self._is_valid_vrn(match):
                        candidates.append((match, pattern_name))
                        logger.debug(f"Found VRN candidate: '{match}' (pattern: {pattern_name})")
        
        if not candidates:
            return None
        
        # If multiple candidates, pick the best one
        best_vrn = self._select_best_vrn(candidates, text)
        
        if best_vrn:
            logger.info(f"✅ Extracted VRN: '{best_vrn}'")
            return best_vrn
        
        return None
    
    
    def extract_all_vrns(self, text: str) -> List[str]:
        """
        Extract all Vehicle Registration Numbers from text.
        
        Args:
            text: Text to search for VRNs
            
        Returns:
            List of VRN strings found
        """
        if not text or len(text.strip()) < 5:
            return []
        
        vrns = []
        seen = set()
        
        for pattern, pattern_name in self.COMPILED_PATTERNS:
            matches = pattern.findall(text)
            
            for match in matches:
                match_upper = match.upper()
                
                if match_upper not in seen and self._is_valid_vrn(match):
                    vrns.append(match_upper)
                    seen.add(match_upper)
        
        logger.info(f"📋 Found {len(vrns)} VRNs in text")
        return vrns
    
    
    def _is_valid_vrn(self, vrn: str) -> bool:
        """
        Validate if a potential VRN is actually a valid Irish VRN.
        
        Args:
            vrn: Potential VRN string
            
        Returns:
            True if valid VRN, False otherwise
        """
        if not vrn or len(vrn) < 5:
            return False
        
        vrn_upper = vrn.upper()
        
        # Check if it matches false positive patterns (dates, phone numbers)
        for false_pattern in self.COMPILED_FALSE_POSITIVES:
            if false_pattern.match(vrn):
                logger.debug(f"Filtered out false positive: '{vrn}'")
                return False
        
        # Extract county code from VRN
        county_code = self._extract_county_code(vrn_upper)
        
        if not county_code:
            return False
        
        # Validate county code (optional - can be strict or lenient)
        # For now, we accept any letter code as county code might be abbreviated
        # Uncomment below for strict validation:
        # if county_code not in self.VALID_COUNTY_CODES:
        #     logger.debug(f"Invalid county code: '{county_code}' in VRN '{vrn}'")
        #     return False
        
        return True
    
    
    def _extract_county_code(self, vrn: str) -> Optional[str]:
        """
        Extract county code from VRN.
        
        Args:
            vrn: VRN string
            
        Returns:
            County code if found, None otherwise
        """
        # Try to extract county code from VRN
        # Format: YYY-CC-NNNNN or YY-CC-NNNNN
        parts = vrn.split('-')
        
        if len(parts) >= 2:
            # Second part should be county code
            county_code = parts[1]
            if county_code.isalpha() and 1 <= len(county_code) <= 2:
                return county_code.upper()
        
        # Try without hyphens: YYYCCNNNNN
        # Extract letters after initial digits
        match = re.search(r'^\d{2,3}([A-Z]{1,2})\d+$', vrn, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        
        return None
    
    
    def _select_best_vrn(self, candidates: List[Tuple[str, str]], text: str) -> Optional[str]:
        """
        Select the best VRN from multiple candidates.
        
        Priority:
        1. VRN with valid county code
        2. VRN that appears earlier in text
        3. VRN with standard format (with hyphens)
        
        Args:
            candidates: List of (vrn, pattern_name) tuples
            text: Original text
            
        Returns:
            Best VRN string
        """
        if not candidates:
            return None
        
        if len(candidates) == 1:
            return candidates[0][0].upper()
        
        # Score each candidate
        scored_candidates = []
        
        for vrn, pattern_name in candidates:
            score = 0
            vrn_upper = vrn.upper()
            
            # Prefer patterns with hyphens (more standard format)
            if '-' in vrn:
                score += 10
            
            # Prefer new format (3-digit year)
            if pattern_name.startswith('new_format'):
                score += 5
            
            # Prefer earlier occurrence in text
            position = text.upper().find(vrn_upper)
            if position >= 0:
                # Earlier = higher score
                score += max(0, 100 - position)
            
            # Prefer valid county codes
            county_code = self._extract_county_code(vrn_upper)
            if county_code and county_code in self.VALID_COUNTY_CODES:
                score += 20
            
            scored_candidates.append((vrn_upper, score))
        
        # Sort by score (descending)
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        
        best_vrn = scored_candidates[0][0]
        logger.debug(f"Selected best VRN: '{best_vrn}' from {len(candidates)} candidates")
        
        return best_vrn
    
    
    def normalize_vrn(self, vrn: str) -> str:
        """
        Normalize VRN to standard format: YYY-CC-NNNNN
        
        Args:
            vrn: VRN string
            
        Returns:
            Normalized VRN string
        """
        if not vrn:
            return ""
        
        # Remove spaces and convert to uppercase
        vrn_clean = vrn.upper().replace(' ', '')
        
        # If already has hyphens, return as-is
        if '-' in vrn_clean:
            return vrn_clean
        
        # Try to add hyphens based on pattern
        # YYYCCNNNNN -> YYY-CC-NNNNN
        match = re.match(r'^(\d{2,3})([A-Z]{1,2})(\d{1,6})$', vrn_clean)
        if match:
            year, county, number = match.groups()
            return f"{year}-{county}-{number}"
        
        # Return as-is if can't normalize
        return vrn_clean
    
    
    def is_vrn_format(self, text: str) -> bool:
        """
        Quick check if text looks like a VRN (without full validation).
        
        Args:
            text: Text to check
            
        Returns:
            True if text looks like VRN format
        """
        if not text or len(text) < 5:
            return False
        
        for pattern, _ in self.COMPILED_PATTERNS[:4]:  # Check main patterns only
            if pattern.match(text.strip()):
                return True
        
        return False


# Singleton instance
_vrn_patterns = VRNPatterns()


def extract_vrn(text: str) -> Optional[str]:
    """
    Convenience function to extract VRN from text.
    
    Args:
        text: Text to search
        
    Returns:
        VRN if found, None otherwise
    """
    return _vrn_patterns.extract_vrn(text)


def extract_all_vrns(text: str) -> List[str]:
    """
    Convenience function to extract all VRNs from text.
    
    Args:
        text: Text to search
        
    Returns:
        List of VRNs found
    """
    return _vrn_patterns.extract_all_vrns(text)


def normalize_vrn(vrn: str) -> str:
    """
    Convenience function to normalize VRN format.
    
    Args:
        vrn: VRN string
        
    Returns:
        Normalized VRN
    """
    return _vrn_patterns.normalize_vrn(vrn)


def is_vrn_format(text: str) -> bool:
    """
    Convenience function to check if text looks like VRN.
    
    Args:
        text: Text to check
        
    Returns:
        True if looks like VRN
    """
    return _vrn_patterns.is_vrn_format(text)