"""
Advanced Code Detection Engine
Handles messy inputs, extracts up to 3 codes, normalizes formats
"""
import re
import logging
from typing import List, Set

logger = logging.getLogger(__name__)


class CodeDetector:
    """Detects and normalizes resource codes from user messages"""
    
    # Pattern: letters/numbers separated by dash/underscore/space
    # Examples: ABC-123, XYZ_456, AAA 789, abc123
    CODE_PATTERN = re.compile(
        r'\b([A-Za-z0-9]{2,}[-_s]?[A-Za-z0-9]{2,})\b|'  # With separator
        r'\b([A-Z]{3,}[0-9]{2,})\b|'  # Capital letters + numbers
        r'\b([A-Z]{2,}[-_]?[A-Z0-9]{2,})\b'  # Mixed format
    )
    
    MAX_CODES_PER_MESSAGE = 3
    
    @staticmethod
    def normalize_code(code: str) -> str:
        """
        Normalize code to standard format: UPPERCASE with dash
        
        Args:
            code: Raw code string
            
        Returns:
            Normalized code (e.g., ABC-123)
        """
        # Remove extra spaces, convert to uppercase
        code = code.strip().upper()
        
        # Replace underscores and spaces with dash
        code = re.sub(r'[_s]+', '-', code)
        
        # Remove multiple dashes
        code = re.sub(r'-+', '-', code)
        
        # Remove leading/trailing dashes
        code = code.strip('-')
        
        return code
    
    @staticmethod
    def extract_codes(text: str) -> List[str]:
        """
        Extract and normalize up to 3 unique codes from text
        
        Args:
            text: User message text
            
        Returns:
            List of normalized unique codes (max 3)
        """
        if not text or len(text) > 1000:  # Prevent abuse
            return []
        
        # Find all matches
        matches = CodeDetector.CODE_PATTERN.findall(text)
        
        # Flatten tuples and filter empty strings
        raw_codes = [m for match in matches for m in match if m]
        
        # Normalize and deduplicate
        seen: Set[str] = set()
        normalized_codes: List[str] = []
        
        for code in raw_codes:
            normalized = CodeDetector.normalize_code(code)
            
            # Validate length (between 5 and 20 characters)
            if 5 <= len(normalized) <= 20 and normalized not in seen:
                seen.add(normalized)
                normalized_codes.append(normalized)
                
                if len(normalized_codes) >= CodeDetector.MAX_CODES_PER_MESSAGE:
                    break
        
        logger.debug(f"Extracted {len(normalized_codes)} codes: {normalized_codes}")
        return normalized_codes
    
    @staticmethod
    def is_valid_code_format(code: str) -> bool:
        """
        Validate code format
        
        Args:
            code: Code to validate
            
        Returns:
            True if valid format
        """
        normalized = CodeDetector.normalize_code(code)
        return (
            5 <= len(normalized) <= 20 and
            bool(re.match(r'^[A-Z0-9]+(-[A-Z0-9]+)*$', normalized))
        )
