"""
Cryptographic utilities for secure token generation and verification
Production-ready HMAC implementation with constant-time comparison
"""
import secrets
import hmac
import hashlib
import base64
import json
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class CryptoService:
    """Handles all cryptographic operations"""
    
    @staticmethod
    def generate_secret(length: int = 32) -> str:
        """
        Generate cryptographically secure random secret
        
        Args:
            length: Number of bytes (default 32 = 256 bits)
            
        Returns:
            Hex-encoded secret string
        """
        return secrets.token_hex(length)
    
    @staticmethod
    def generate_nonce(length: int = 16) -> str:
        """Generate random nonce for token uniqueness"""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def base64url_encode(data: bytes) -> str:
        """URL-safe base64 encoding without padding"""
        return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')
    
    @staticmethod
    def base64url_decode(data: str) -> bytes:
        """URL-safe base64 decoding with padding restoration"""
        padding = 4 - (len(data) % 4)
        if padding != 4:
            data += '=' * padding
        return base64.urlsafe_b64decode(data.encode('utf-8'))
    
    @staticmethod
    def create_hmac_signature(secret: str, message: str) -> str:
        """
        Create HMAC-SHA256 signature
        
        Args:
            secret: Hex-encoded secret key
            message: Message to sign
            
        Returns:
            Hex-encoded signature
        """
        secret_bytes = bytes.fromhex(secret)
        message_bytes = message.encode('utf-8')
        signature = hmac.new(secret_bytes, message_bytes, hashlib.sha256).digest()
        return signature.hex()
    
    @staticmethod
    def verify_hmac_signature(secret: str, message: str, signature: str) -> bool:
        """
        Verify HMAC signature using constant-time comparison
        
        Args:
            secret: Hex-encoded secret key
            message: Original message
            signature: Hex-encoded signature to verify
            
        Returns:
            True if valid, False otherwise
        """
        try:
            expected_signature = CryptoService.create_hmac_signature(secret, message)
            return hmac.compare_digest(expected_signature, signature)
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return False
    
    @staticmethod
    def create_signed_token(payload: Dict, secret: str) -> str:
        """
        Create signed token with format: base64url(payload).signature
        
        Args:
            payload: Dictionary containing token data
            secret: Hex-encoded secret for signing
            
        Returns:
            Signed token string
        """
        # Serialize payload to JSON
        payload_json = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        payload_b64 = CryptoService.base64url_encode(payload_json.encode('utf-8'))
        
        # Create HMAC signature
        signature = CryptoService.create_hmac_signature(secret, payload_b64)
        
        # Combine: payload.signature
        return f"{payload_b64}.{signature}"
    
    @staticmethod
    def verify_and_decode_token(token: str, secret: str) -> Optional[Dict]:
        """
        Verify token signature and decode payload
        
        Args:
            token: Signed token string
            secret: Hex-encoded secret for verification
            
        Returns:
            Decoded payload dict if valid, None if invalid
        """
        try:
            # Split token
            if '.' not in token:
                logger.warning("Invalid token format: missing separator")
                return None
            
            payload_b64, signature = token.rsplit('.', 1)
            
            # Verify signature
            if not CryptoService.verify_hmac_signature(secret, payload_b64, signature):
                logger.warning("Invalid token signature")
                return None
            
            # Decode payload
            payload_bytes = CryptoService.base64url_decode(payload_b64)
            payload = json.loads(payload_bytes.decode('utf-8'))
            
            return payload
            
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return None
