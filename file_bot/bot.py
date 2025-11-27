"""
FileBot - Handles secure token verification and file delivery
Stateless delivery system with atomic single-use enforcement
"""
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
)
from telegram.error import TelegramError

from database.mongodb import MongoDBManager, db_manager as global_db_manager
from handlers.delivery_handler import DeliveryHandler
from config import Config

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('file_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class FileBot:
    """FileBot Application - Secure File Delivery"""
    
    def __init__(self, config: Config):
        self.config = config
        self.application: Application = None
        self.db_manager: MongoDBManager = None
        
    async def initialize(self):
        """Initialize bot and database"""
        try:
            global global_db_manager
            self.db_manager = MongoDBManager(
                self.config.MONGODB_URI,
                self.config.MONGODB_DATABASE
            )
            await self.db_manager.connect()
            global_db_manager = self.db_manager
            
            logger.info("✅ FileBot initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            raise
    
    def build_application(self) -> Application:
        """Build application with delivery handler"""
        self.application = (
            Application.builder()
            .token(self.config.FILE_BOT_TOKEN)
            .concurrent_updates(True)
            .build()
        )
        
        db = self.db_manager.db
        delivery_handler = DeliveryHandler(db, self.config)
        
        # /start handler with deep linking for token redemption
        self.application.add_handler(
            CommandHandler("start", delivery_handler.handle_start)
        )
        
        # Error handler
        self.application.add_error_handler(self._error_handler)
        
        logger.info("✅ FileBot application built")
        return self.application
    
    async def _error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "⚠️ An error occurred. Please try again."
                )
            except TelegramError:
                pass
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down FileBot...")
        if self.db_manager:
            await self.db_manager.close()
        logger.info("✅ FileBot shutdown complete")
    
    def run(self):
        """Run the bot"""
        try:
            logger.info("🚀 Starting FileBot...")
            self.application.run_polling(allowed_updates=Update.ALL_TYPES)
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Bot crashed: {e}")
            raise


async def main():
    """Main entry point"""
    config = Config()
    bot = FileBot(config)
    
    await bot.initialize()
    bot.build_application()
    bot.run()


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
