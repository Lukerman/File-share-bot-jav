"""
Configuration Management
Load from environment variables with validation
"""
import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()


class Config:
    """Application configuration"""
    
    # Telegram Bot Tokens
    MAIN_BOT_TOKEN: str = os.getenv('MAIN_BOT_TOKEN')
    FILE_BOT_TOKEN: str = os.getenv('FILE_BOT_TOKEN')
    
    # MongoDB
    MONGODB_URI: str = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
    MONGODB_DATABASE: str = os.getenv('MONGODB_DATABASE', 'file_provider_db')
    
    # Admin Configuration
    MAIN_ADMIN_ID: int = int(os.getenv('MAIN_ADMIN_ID'))
    DATABASE_CHANNEL_ID: int = int(os.getenv('DATABASE_CHANNEL_ID'))
    REQUEST_CHANNEL_ID: int = int(os.getenv('REQUEST_CHANNEL_ID'))
    
    # Mini WebApp
    MINI_WEBAPP_URL: str = os.getenv('MINI_WEBAPP_URL')
    
    # Security
    MASTER_SECRET_KEY: str = os.getenv('MASTER_SECRET_KEY')
    
    # Bot Settings
    GROUP_MESSAGE_DELETE_DELAY: int = 60  # seconds
    REQUEST_EXPIRY_DAYS: int = 7
    
    def validate(self) -> bool:
        """Validate required configuration"""
        required = [
            'MAIN_BOT_TOKEN',
            'FILE_BOT_TOKEN',
            'MAIN_ADMIN_ID',
            'DATABASE_CHANNEL_ID',
            'REQUEST_CHANNEL_ID',
            'MINI_WEBAPP_URL',
            'MASTER_SECRET_KEY'
        ]
        
        missing = [field for field in required if not getattr(self, field, None)]
        
        if missing:
            raise ValueError(f"Missing required config: {', '.join(missing)}")
        
        return True
