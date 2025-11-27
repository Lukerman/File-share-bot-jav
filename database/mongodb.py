"""
MongoDB Connection and Management
Production-ready with connection pooling, retry logic, and monitoring
"""
import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.errors import ConnectionFailure, OperationFailure
import asyncio

logger = logging.getLogger(__name__)


class MongoDBManager:
    """Manages MongoDB connections with production-grade features"""
    
    def __init__(self, uri: str, database: str):
        self.uri = uri
        self.database_name = database
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        
    async def connect(self, max_retries: int = 3) -> None:
        """
        Establish database connection with retry logic
        
        Args:
            max_retries: Maximum number of connection attempts
        """
        for attempt in range(max_retries):
            try:
                self.client = AsyncIOMotorClient(
                    self.uri,
                    maxPoolSize=50,
                    minPoolSize=10,
                    maxIdleTimeMS=45000,
                    serverSelectionTimeoutMS=5000,
                    retryWrites=True,
                    w='majority'
                )
                
                # Test connection
                await self.client.admin.command('ping')
                self.db = self.client[self.database_name]
                
                await self._create_indexes()
                logger.info(f"✅ MongoDB connected successfully to {self.database_name}")
                return
                
            except ConnectionFailure as e:
                logger.error(f"Connection attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
                    
    async def _create_indexes(self) -> None:
        """Create all required indexes with optimal settings"""
        try:
            # Videos Collection Indexes
            await self.db.videos.create_indexes([
                IndexModel([("code", ASCENDING)], unique=True, name="code_unique_idx"),
                IndexModel([("code", ASCENDING), ("version", ASCENDING)], name="code_version_idx"),
                IndexModel([("created_at", DESCENDING)], name="created_at_idx"),
                IndexModel([("file_secret", ASCENDING)], sparse=True, name="file_secret_idx"),
            ])
            
            # Requests Collection with TTL
            await self.db.requests.create_indexes([
                IndexModel([("code", ASCENDING)], unique=True, name="code_request_idx"),
                IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0, name="ttl_idx"),
                IndexModel([("created_at", DESCENDING)], name="request_created_idx"),
            ])
            
            # Tokens Collection - Single-use enforcement
            await self.db.tokens.create_indexes([
                IndexModel([("token", ASCENDING)], unique=True, name="token_unique_idx"),
                IndexModel(
                    [("resource_id", ASCENDING), ("version", ASCENDING)],
                    name="resource_version_idx"
                ),
                IndexModel([("used", ASCENDING), ("created_at", DESCENDING)], name="used_status_idx"),
            ])
            
            # Admins Collection
            await self.db.admins.create_indexes([
                IndexModel([("user_id", ASCENDING)], unique=True, name="admin_user_idx"),
                IndexModel([("role", ASCENDING)], name="admin_role_idx"),
            ])
            
            # Groups Collection
            await self.db.groups.create_indexes([
                IndexModel([("group_id", ASCENDING)], unique=True, name="group_id_idx"),
                IndexModel([("approved", ASCENDING)], name="approved_idx"),
            ])
            
            # Users Collection - Spam Protection
            await self.db.users.create_indexes([
                IndexModel([("user_id", ASCENDING)], unique=True, name="user_id_idx"),
                IndexModel([("banned", ASCENDING), ("ban_until", ASCENDING)], name="ban_status_idx"),
            ])
            
            logger.info("✅ All indexes created successfully")
            
        except OperationFailure as e:
            logger.error(f"Index creation failed: {e}")
            raise
            
    async def close(self) -> None:
        """Gracefully close database connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
            
    def get_collection(self, name: str):
        """Get collection by name with type safety"""
        if not self.db:
            raise RuntimeError("Database not connected")
        return self.db[name]


# Global database instance
db_manager: Optional[MongoDBManager] = None


async def get_database() -> AsyncIOMotorDatabase:
    """Get database instance - dependency injection pattern"""
    if not db_manager or not db_manager.db:
        raise RuntimeError("Database not initialized")
    return db_manager.db
