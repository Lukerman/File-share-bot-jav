"""
Advanced Spam Protection and Rate Limiting
Progressive warnings, cooldowns, and temporary/permanent bans
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class SpamProtection:
    """Manages user rate limiting and anti-spam measures"""
    
    # Progressive cooldown periods (seconds)
    COOLDOWNS = {
        0: 0,      # No warnings
        1: 10,     # 1st warning: 10 seconds
        2: 30,     # 2nd warning: 30 seconds
        3: 120,    # 3rd warning: 2 minutes
        4: 600,    # 4th warning: 10 minutes
    }
    
    AUTO_BAN_WARNINGS = 5
    TEMP_BAN_DURATION = timedelta(hours=24)
    
    REQUEST_LIMIT = 10  # Max requests per minute
    REQUEST_WINDOW = timedelta(minutes=1)
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        
    async def check_user_permission(self, user_id: int) -> Tuple[bool, Optional[str]]:
        """
        Check if user is allowed to make requests
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Tuple of (allowed: bool, reason: Optional[str])
        """
        try:
            user = await self.db.users.find_one({"user_id": user_id})
            
            if not user:
                # First time user - create profile
                await self._create_user_profile(user_id)
                return (True, None)
            
            now = datetime.utcnow()
            
            # Check permanent ban
            if user.get('banned') and not user.get('ban_until'):
                return (False, "You are permanently banned")
            
            # Check temporary ban
            if user.get('ban_until') and user['ban_until'] > now:
                remaining = user['ban_until'] - now
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                return (False, f"Temporarily banned. Time remaining: {hours}h {minutes}m")
            
            # Lift expired temp ban
            if user.get('ban_until') and user['ban_until'] <= now:
                await self.db.users.update_one(
                    {"user_id": user_id},
                    {"$set": {"banned": False, "ban_until": None}}
                )
            
            # Check cooldown
            if user.get('cooldown_until') and user['cooldown_until'] > now:
                remaining = int((user['cooldown_until'] - now).total_seconds())
                return (False, f"Please wait {remaining} seconds before next request")
            
            return (True, None)
            
        except Exception as e:
            logger.error(f"Permission check failed: {e}")
            return (True, None)  # Fail open to avoid blocking legitimate users
    
    async def check_rate_limit(self, user_id: int) -> bool:
        """
        Check if user exceeded rate limit
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if within limit, False if exceeded
        """
        try:
            user = await self.db.users.find_one({"user_id": user_id})
            if not user:
                return True
            
            now = datetime.utcnow()
            last_request = user.get('last_request')
            
            # Reset counter if window expired
            if not last_request or (now - last_request) > self.REQUEST_WINDOW:
                await self.db.users.update_one(
                    {"user_id": user_id},
                    {"$set": {"request_count": 1, "last_request": now}}
                )
                return True
            
            # Check if limit exceeded
            if user.get('request_count', 0) >= self.REQUEST_LIMIT:
                return False
            
            # Increment counter
            await self.db.users.update_one(
                {"user_id": user_id},
                {
                    "$inc": {"request_count": 1},
                    "$set": {"last_request": now}
                }
            )
            return True
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            return True
    
    async def issue_warning(self, user_id: int, reason: str = "Spam detected") -> Dict:
        """
        Issue warning to user and apply progressive cooldown
        
        Args:
            user_id: Telegram user ID
            reason: Warning reason
            
        Returns:
            Dict with warning details
        """
        try:
            user = await self.db.users.find_one({"user_id": user_id})
            if not user:
                await self._create_user_profile(user_id)
                user = await self.db.users.find_one({"user_id": user_id})
            
            warning_count = user.get('warning_count', 0) + 1
            
            # Auto-ban if threshold reached
            if warning_count >= self.AUTO_BAN_WARNINGS:
                await self.ban_user(user_id, duration=self.TEMP_BAN_DURATION, reason="Excessive warnings")
                return {
                    "action": "banned",
                    "duration": str(self.TEMP_BAN_DURATION),
                    "reason": reason
                }
            
            # Apply cooldown
            cooldown_seconds = self.COOLDOWNS.get(warning_count, 600)
            cooldown_until = datetime.utcnow() + timedelta(seconds=cooldown_seconds)
            
            await self.db.users.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "warning_count": warning_count,
                        "cooldown_until": cooldown_until
                    }
                }
            )
            
            logger.info(f"Warning issued to user {user_id}: {warning_count}/5")
            return {
                "action": "warning",
                "count": warning_count,
                "cooldown": cooldown_seconds,
                "reason": reason
            }
            
        except Exception as e:
            logger.error(f"Failed to issue warning: {e}")
            return {"action": "error"}
    
    async def ban_user(
        self,
        user_id: int,
        duration: Optional[timedelta] = None,
        reason: str = "Violation of terms"
    ) -> bool:
        """
        Ban user temporarily or permanently
        
        Args:
            user_id: Telegram user ID
            duration: Ban duration (None = permanent)
            reason: Ban reason
            
        Returns:
            True if successful
        """
        try:
            ban_until = None if not duration else datetime.utcnow() + duration
            
            await self.db.users.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "banned": True,
                        "ban_until": ban_until,
                        "ban_reason": reason
                    }
                },
                upsert=True
            )
            
            ban_type = "permanently" if not duration else f"for {duration}"
            logger.info(f"User {user_id} banned {ban_type}: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to ban user: {e}")
            return False
    
    async def unban_user(self, user_id: int) -> bool:
        """Unban user and reset warnings"""
        try:
            await self.db.users.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "banned": False,
                        "ban_until": None,
                        "ban_reason": None,
                        "warning_count": 0
                    }
                }
            )
            logger.info(f"User {user_id} unbanned")
            return True
        except Exception as e:
            logger.error(f"Failed to unban user: {e}")
            return False
    
    async def _create_user_profile(self, user_id: int, username: Optional[str] = None):
        """Create new user profile"""
        await self.db.users.insert_one({
            "user_id": user_id,
            "username": username,
            "first_seen": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "warning_count": 0,
            "banned": False,
            "request_count": 0,
            "total_downloads": 0,
            "total_requests": 0
        })
