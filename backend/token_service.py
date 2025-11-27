"""
Token Service - Handles token generation and management
Production-ready with atomic operations and proper error handling
"""
import logging
from typing import Optional, Dict
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from .crypto_utils import CryptoService
from database.models import Token

logger = logging.getLogger(__name__)


class TokenService:
    """Manages secure token lifecycle"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.crypto = CryptoService()
        
    async def generate_token(
        self,
        resource_id: str,
        version: str,
        file_secret: str
    ) -> Optional[str]:
        """
        Generate new permanent unlock token
        
        Args:
            resource_id: Resource code
            version: File version
            file_secret: Per-file secret for HMAC
            
        Returns:
            Signed token string or None on error
        """
        try:
            # Create payload with nonce for uniqueness
            nonce = self.crypto.generate_nonce()
            payload = {
                "resource_id": resource_id.upper(),
                "version": version,
                "nonce": nonce
            }
            
            # Generate signed token
            token = self.crypto.create_signed_token(payload, file_secret)
            
            # Store token in database
            token_doc = Token(
                token=token,
                resource_id=resource_id.upper(),
                version=version,
                nonce=nonce,
                used=False
            )
            
            await self.db.tokens.insert_one(token_doc.dict())
            
            logger.info(f"Token generated for {resource_id} v{version}")
            return token
            
        except DuplicateKeyError:
            logger.warning(f"Duplicate token generated (rare collision), retrying...")
            # Retry once with new nonce
            return await self.generate_token(resource_id, version, file_secret)
            
        except Exception as e:
            logger.error(f"Token generation failed: {e}")
            return None
    
    async def verify_and_consume_token(
        self,
        token: str,
        user_id: int,
        ip_address: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Verify token and mark as used atomically (single-use enforcement)
        
        Args:
            token: Token string to verify
            user_id: User attempting to redeem
            ip_address: Optional IP for logging
            
        Returns:
            Resource info dict if valid, None if invalid/used
        """
        try:
            # Atomic find and update - ensures single-use
            result = await self.db.tokens.find_one_and_update(
                {
                    "token": token,
                    "used": False  # Critical: only match unused tokens
                },
                {
                    "$set": {
                        "used": True,
                        "used_at": datetime.utcnow(),
                        "used_by": user_id,
                        "ip_address": ip_address
                    }
                },
                return_document=False  # Return original document
            )
            
            if not result:
                # Token already used or doesn't exist
                existing = await self.db.tokens.find_one({"token": token})
                if existing and existing.get("used"):
                    logger.warning(f"Token already used by user {existing.get('used_by')}")
                else:
                    logger.warning("Token not found or invalid")
                return None
            
            # Verify signature with file secret
            file_secret = await self._get_file_secret(
                result['resource_id'],
                result['version']
            )
            
            if not file_secret:
                logger.error("File secret not found")
                return None
            
            payload = self.crypto.verify_and_decode_token(token, file_secret)
            if not payload:
                logger.error("Token signature verification failed")
                return None
            
            # Validate payload matches stored data
            if (payload['resource_id'] != result['resource_id'] or
                payload['version'] != result['version']):
                logger.error("Token payload mismatch")
                return None
            
            logger.info(f"Token consumed successfully by user {user_id}")
            return {
                "resource_id": result['resource_id'],
                "version": result['version']
            }
            
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return None
    
    async def _get_file_secret(self, resource_id: str, version: str) -> Optional[str]:
        """Retrieve file secret from videos collection"""
        try:
            video = await self.db.videos.find_one({"code": resource_id.upper()})
            return video.get('file_secret') if video else None
        except Exception as e:
            logger.error(f"Failed to retrieve file secret: {e}")
            return None
    
    async def revoke_tokens(self, resource_id: str, version: Optional[str] = None) -> int:
        """
        Revoke all tokens for a resource/version
        
        Args:
            resource_id: Resource code
            version: Specific version or None for all
            
        Returns:
            Number of tokens revoked
        """
        try:
            query = {"resource_id": resource_id.upper(), "used": False}
            if version:
                query["version"] = version
            
            result = await self.db.tokens.update_many(
                query,
                {"$set": {"used": True, "used_at": datetime.utcnow()}}
            )
            
            logger.info(f"Revoked {result.modified_count} tokens for {resource_id}")
            return result.modified_count
            
        except Exception as e:
            logger.error(f"Token revocation failed: {e}")
            return 0
    
    async def rotate_file_secret(self, resource_id: str) -> bool:
        """
        Rotate file secret and revoke all existing tokens
        
        Args:
            resource_id: Resource code
            
        Returns:
            True if successful
        """
        try:
            # Generate new secret
            new_secret = self.crypto.generate_secret()
            
            # Update video document
            result = await self.db.videos.update_one(
                {"code": resource_id.upper()},
                {"$set": {"file_secret": new_secret}}
            )
            
            if result.modified_count == 0:
                logger.error(f"Resource {resource_id} not found")
                return False
            
            # Revoke all existing tokens
            await self.revoke_tokens(resource_id)
            
            logger.info(f"File secret rotated for {resource_id}")
            return True
            
        except Exception as e:
            logger.error(f"Secret rotation failed: {e}")
            return False
