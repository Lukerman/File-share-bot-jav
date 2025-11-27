"""
Delivery Handler - Token verification and file delivery
Implements atomic single-use enforcement with HMAC verification
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime

from backend.token_service import TokenService

logger = logging.getLogger(__name__)


class DeliveryHandler:
    """Handles secure file delivery with token verification"""
    
    def __init__(self, db, config):
        self.db = db
        self.config = config
        self.token_service = TokenService(db)
        
    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /start command with deep linking
        Format: /start TOKEN or just /start
        """
        user_id = update.effective_user.id
        
        # Check for token parameter
        if not context.args or len(context.args) == 0:
            await update.message.reply_text(
                "👋 **Welcome to FileBot!**

"
                "This bot delivers files after ad verification.

"
                "You'll be redirected here automatically after watching ads.
"
                "Don't send commands manually.",
                parse_mode='Markdown'
            )
            return
        
        token = context.args[0]
        
        # Get user IP (if available via webhook)
        ip_address = None
        
        # Verify and consume token atomically
        result = await self.token_service.verify_and_consume_token(
            token,
            user_id,
            ip_address
        )
        
        if not result:
            await update.message.reply_text(
                "❌ **Invalid or Expired Token**

"
                "This token has already been used or is invalid.

"
                "Possible reasons:
"
                "• Token already redeemed
"
                "• Token expired
"
                "• Invalid signature

"
                "Please generate a new unlock token from the main bot.",
                parse_mode='Markdown'
            )
            logger.warning(f"Invalid token redemption attempt by user {user_id}")
            return
        
        # Token valid - deliver file
        resource_id = result['resource_id']
        version = result['version']
        
        await self._deliver_file(update, context, resource_id, version, user_id)
    
    async def _deliver_file(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        resource_id: str,
        version: str,
        user_id: int
    ):
        """Deliver file to user"""
        try:
            # Get video document
            video = await self.db.videos.find_one({"code": resource_id.upper()})
            
            if not video:
                await update.message.reply_text("❌ File no longer available.")
                logger.error(f"Video {resource_id} not found during delivery")
                return
            
            # Find specific version
            versions = video.get('versions', [])
            target_version = next(
                (v for v in versions if v['version'] == version),
                None
            )
            
            if not target_version:
                await update.message.reply_text("❌ Requested version not found.")
                logger.error(f"Version {version} not found for {resource_id}")
                return
            
            # Send file
            file_id = target_version['file_id']
            file_type = target_version['file_type']
            file_name = target_version.get('file_name', f"{resource_id}_{version}")
            
            caption = (
                f"✅ **{resource_id} v{version}**

"
                f"📦 File delivered successfully!
"
                f"📊 Total versions available: {len(versions)}"
            )
            
            # Send based on file type
            if file_type == 'document':
                await context.bot.send_document(
                    chat_id=user_id,
                    document=file_id,
                    caption=caption,
                    parse_mode='Markdown'
                )
            elif file_type == 'video':
                await context.bot.send_video(
                    chat_id=user_id,
                    video=file_id,
                    caption=caption,
                    parse_mode='Markdown'
                )
            elif file_type == 'audio':
                await context.bot.send_audio(
                    chat_id=user_id,
                    audio=file_id,
                    caption=caption,
                    parse_mode='Markdown'
                )
            
            # Send action buttons
            keyboard = []
            
            # Show other versions
            if len(versions) > 1:
                keyboard.append([
                    InlineKeyboardButton(
                        f"📋 View All {len(versions)} Versions",
                        callback_data=f"versions_{resource_id}"
                    )
                ])
            
            # Regenerate token button
            keyboard.append([
                InlineKeyboardButton(
                    "🔄 Get New Unlock Token",
                    callback_data="regenerate_token"
                )
            ])
            
            # Report issue
            keyboard.append([
                InlineKeyboardButton(
                    "⚠️ Report Issue",
                    callback_data=f"report_{resource_id}"
                )
            ])
            
            await update.message.reply_text(
                "🎉 **Enjoy your file!**

"
                "Need another version or have issues?",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
            # Update statistics
            await self.db.videos.update_one(
                {"code": resource_id.upper()},
                {"$inc": {"total_downloads": 1}}
            )
            
            await self.db.users.update_one(
                {"user_id": user_id},
                {
                    "$inc": {"total_downloads": 1},
                    "$set": {"last_activity": datetime.utcnow()}
                },
                upsert=True
            )
            
            # Store last delivery in context for regenerate feature
            context.user_data['last_delivery'] = {
                "code": resource_id,
                "version": version
            }
            
            logger.info(f"File delivered: {resource_id} v{version} to user {user_id}")
            
        except Exception as e:
            logger.error(f"File delivery failed: {e}")
            await update.message.reply_text(
                "❌ File delivery failed. Please contact support."
          )
