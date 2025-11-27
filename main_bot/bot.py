"""
Main Bot - Handles code detection, search, requests, and admin operations
Production-ready with comprehensive error handling and logging
"""
import logging
import os
from datetime import datetime
from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)
from telegram.error import TelegramError

from database.mongodb import MongoDBManager, db_manager as global_db_manager
from handlers.group_handler import GroupHandler
from handlers.search_handler import SearchHandler
from handlers.request_handler import RequestHandler
from handlers.admin_handler import AdminHandler
from handlers.help_handler import HelpHandler
from config import Config

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('main_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MainBot:
    """Main Bot Application"""
    
    def __init__(self, config: Config):
        self.config = config
        self.application: Application = None
        self.db_manager: MongoDBManager = None
        
    async def initialize(self):
        """Initialize bot and database connections"""
        try:
            # Initialize database
            global global_db_manager
            self.db_manager = MongoDBManager(
                self.config.MONGODB_URI,
                self.config.MONGODB_DATABASE
            )
            await self.db_manager.connect()
            global_db_manager = self.db_manager
            
            # Ensure main admin exists
            await self._ensure_main_admin()
            
            logger.info("✅ Main Bot initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            raise
    
    async def _ensure_main_admin(self):
        """Ensure main admin is registered in database"""
        try:
            db = self.db_manager.db
            existing = await db.admins.find_one({"user_id": self.config.MAIN_ADMIN_ID})
            
            if not existing:
                await db.admins.insert_one({
                    "user_id": self.config.MAIN_ADMIN_ID,
                    "role": "main_admin",
                    "added_by": self.config.MAIN_ADMIN_ID,
                    "added_at": datetime.utcnow(),
                    "permissions": {"all": True}
                })
                logger.info(f"Main admin {self.config.MAIN_ADMIN_ID} registered")
                
        except Exception as e:
            logger.error(f"Failed to register main admin: {e}")
    
    def build_application(self) -> Application:
        """Build and configure the application with all handlers"""
        # Create application
        self.application = (
            Application.builder()
            .token(self.config.MAIN_BOT_TOKEN)
            .concurrent_updates(True)
            .build()
        )
        
        db = self.db_manager.db
        
        # Initialize handlers
        group_handler = GroupHandler(db, self.config)
        search_handler = SearchHandler(db, self.config)
        request_handler = RequestHandler(db, self.config)
        admin_handler = AdminHandler(db, self.config)
        help_handler = HelpHandler()
        
        # Command handlers
        self.application.add_handler(CommandHandler("start", help_handler.start))
        self.application.add_handler(CommandHandler("help", help_handler.help_command))
        self.application.add_handler(CommandHandler("approvegroup", group_handler.approve_group))
        self.application.add_handler(CommandHandler("adminpanel", admin_handler.show_admin_panel))
        
        # Group membership handlers (must be before message handlers)
        self.application.add_handler(
            MessageHandler(
                filters.StatusUpdate.NEW_CHAT_MEMBERS,
                group_handler.on_bot_added
            )
        )
        
        # Callback query handler for inline buttons
        self.application.add_handler(CallbackQueryHandler(self._handle_callback))
        
        # Message handler for code detection (groups and private)
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                search_handler.handle_message
            )
        )
        
        # Error handler
        self.application.add_error_handler(self._error_handler)
        
        # Store handler instances for callback routing
        self.application.bot_data['handlers'] = {
            'group': group_handler,
            'search': search_handler,
            'request': request_handler,
            'admin': admin_handler,
            'help': help_handler
        }
        
        logger.info("✅ Application built with all handlers")
        return self.application
    
    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Route callback queries to appropriate handlers"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        handlers = context.bot_data['handlers']
        
        try:
            # Route based on callback data prefix
            if data.startswith('view_'):
                await handlers['search'].handle_view_details(update, context)
            elif data.startswith('unlock_'):
                await handlers['search'].handle_unlock(update, context)
            elif data.startswith('request_'):
                await handlers['request'].handle_request_callback(update, context)
            elif data.startswith('admin_'):
                await handlers['admin'].handle_admin_callback(update, context)
            elif data == 'regenerate_token':
                await handlers['search'].handle_regenerate_token(update, context)
            else:
                await query.edit_message_text("Unknown action")
                
        except Exception as e:
            logger.error(f"Callback handling error: {e}")
            await query.edit_message_text("An error occurred. Please try again.")
    
    async def _error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "⚠️ An error occurred. Please try again later."
                )
            except TelegramError:
                pass
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down Main Bot...")
        if self.db_manager:
            await self.db_manager.close()
        logger.info("✅ Main Bot shutdown complete")
    
    def run(self):
        """Run the bot with polling"""
        try:
            logger.info("🚀 Starting Main Bot...")
            self.application.run_polling(allowed_updates=Update.ALL_TYPES)
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Bot crashed: {e}")
            raise


async def main():
    """Main entry point"""
    config = Config()
    bot = MainBot(config)
    
    await bot.initialize()
    bot.build_application()
    bot.run()


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
