"""
Pydantic Models for Data Validation and Type Safety
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class AdminRole(str, Enum):
    MAIN_ADMIN = "main_admin"
    ADMIN = "admin"
    MODERATOR = "moderator"


class VideoVersion(BaseModel):
    """Individual file version"""
    version: str
    file_id: str
    file_type: str  # document, video, audio, etc.
    file_size: Optional[int] = None
    uploaded_by: int
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    file_name: Optional[str] = None


class Video(BaseModel):
    """Main resource document"""
    code: str  # Normalized code (e.g., ABC-123)
    versions: List[VideoVersion] = []
    file_secret: str  # Per-file 32-byte secret for HMAC
    description: Optional[str] = None
    tags: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    total_downloads: int = 0
    active: bool = True
    
    @validator('code')
    def normalize_code(cls, v):
        return v.upper().strip()


class Request(BaseModel):
    """User request for unavailable resource"""
    code: str
    requesters: List[int] = []  # List of user IDs
    request_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(
        default_factory=lambda: datetime.utcnow() + timedelta(days=7)
    )
    
    @validator('code')
    def normalize_code(cls, v):
        return v.upper().strip()


class Token(BaseModel):
    """Secure unlock token - single-use, permanent (no expiry)"""
    token: str  # Full token with signature
    resource_id: str
    version: str
    nonce: str
    used: bool = False
    used_at: Optional[datetime] = None
    used_by: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None


class Admin(BaseModel):
    """Admin user"""
    user_id: int
    role: AdminRole
    username: Optional[str] = None
    added_by: int
    added_at: datetime = Field(default_factory=datetime.utcnow)
    permissions: Dict[str, bool] = Field(default_factory=dict)


class Group(BaseModel):
    """Telegram group configuration"""
    group_id: int
    group_title: Optional[str] = None
    approved: bool = False
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    added_at: datetime = Field(default_factory=datetime.utcnow)
    message_delete_delay: int = 60  # seconds


class User(BaseModel):
    """User spam protection and tracking"""
    user_id: int
    username: Optional[str] = None
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    
    # Spam protection
    warning_count: int = 0
    banned: bool = False
    ban_until: Optional[datetime] = None
    ban_reason: Optional[str] = None
    
    # Rate limiting
    request_count: int = 0
    last_request: Optional[datetime] = None
    cooldown_until: Optional[datetime] = None
    
    # Statistics
    total_downloads: int = 0
    total_requests: int = 0
