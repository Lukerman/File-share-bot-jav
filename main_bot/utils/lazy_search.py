"""
Lazy Search Engine with Fuzzy Matching
Provides typo correction and close-match suggestions
"""
import logging
from typing import List, Dict, Optional, Tuple
from fuzzywuzzy import fuzz, process
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class LazySearchEngine:
    """Fuzzy search engine for resource codes"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.similarity_threshold = 75  # Minimum similarity score (0-100)
        self.max_suggestions = 3
        
    async def search_exact(self, code: str) -> Optional[Dict]:
        """
        Search for exact code match
        
        Args:
            code: Normalized code
            
        Returns:
            Video document or None
        """
        try:
            result = await self.db.videos.find_one(
                {"code": code.upper(), "active": True}
            )
            return result
        except Exception as e:
            logger.error(f"Exact search failed: {e}")
            return None
    
    async def search_fuzzy(self, code: str) -> List[Dict]:
        """
        Fuzzy search with typo correction and suggestions
        
        Args:
            code: User-provided code (potentially misspelled)
            
        Returns:
            List of suggested matches with similarity scores
        """
        try:
            # Get all active codes
            all_videos = await self.db.videos.find(
                {"active": True},
                {"code": 1, "description": 1, "versions": 1}
            ).to_list(length=None)
            
            if not all_videos:
                return []
            
            # Extract codes for matching
            all_codes = [v['code'] for v in all_videos]
            
            # Find best matches using fuzzy matching
            matches = process.extract(
                code.upper(),
                all_codes,
                scorer=fuzz.ratio,
                limit=self.max_suggestions
            )
            
            # Filter by threshold and prepare results
            suggestions = []
            for matched_code, score in matches:
                if score >= self.similarity_threshold:
                    video = next(v for v in all_videos if v['code'] == matched_code)
                    suggestions.append({
                        "code": matched_code,
                        "score": score,
                        "description": video.get('description', ''),
                        "version_count": len(video.get('versions', []))
                    })
            
            logger.info(f"Fuzzy search for '{code}' found {len(suggestions)} matches")
            return suggestions
            
        except Exception as e:
            logger.error(f"Fuzzy search failed: {e}")
            return []
    
    async def smart_search(self, code: str) -> Tuple[Optional[Dict], List[Dict]]:
        """
        Smart search: try exact first, then fuzzy
        
        Args:
            code: User-provided code
            
        Returns:
            Tuple of (exact_match, fuzzy_suggestions)
        """
        # Try exact match first
        exact = await self.search_exact(code)
        
        if exact:
            return (exact, [])
        
        # Fall back to fuzzy search
        suggestions = await self.search_fuzzy(code)
        return (None, suggestions)
    
    async def search_by_keywords(self, keywords: str, limit: int = 10) -> List[Dict]:
        """
        Search by description keywords
        
        Args:
            keywords: Search terms
            limit: Maximum results
            
        Returns:
            List of matching videos
        """
        try:
            # MongoDB text search (requires text index)
            results = await self.db.videos.find(
                {
                    "$text": {"$search": keywords},
                    "active": True
                },
                {"score": {"$meta": "textScore"}}
            ).sort(
                [("score", {"$meta": "textScore"})]
            ).limit(limit).to_list(length=limit)
            
            return results
            
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []
