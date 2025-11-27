"""
Group Management Handler
Handles bot addition, group approval, and auto-leave logic
"""
import logging
from telegram import Update, ChatMember
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from datetime import datetime

logger = logging.getLogger(__name__)


class GroupHandler:
    """Manages group operations and permissions"""
    
    def __init__(self, db, config):
        self.db = db
        self.config = config
        
    async def on_bot_added(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle bot being added to group
        Logic: Main admin add = auto-approve, others = check approval
        """
        message = update.message
        chat = message.chat
        
        if chat.type not in ['group', 'supergroup']:
            return
        
        # Check if bot was added
        bot_added = any(
            member.id == context.bot.id 
            for member in message.new_chat_members
        )
        
        if not bot_added:
            return
        
        try:
            # Get the user who added the bot
            added_by = message.from_user.id
            
            # Check if added by main admin
            if added_by == self.config.MAIN_ADMIN_ID:
                await self._auto_approve_group(chat.id, chat.title, added_by)
                await message.reply_text(
                    "✅ **Bot Activated!**

"
                    "Send any code like ABC-123 to search for files.
"
                    "Use /help for more information.",
                    parse_mode='Markdown'
                )
                logger.info(f"Auto-approved group {chat.id} by main admin")
                return
            
            # Check if group is already approved
            group = await self.db.groups.find_one({"group_id": chat.id})
            
            if group and group.get('approved'):
                await message.reply_text(
                    "✅ Bot is active in this group!
"
                    "Send codes to search for files.",
                    parse_mode='Markdown'
                )
                return
            
            # Not approved - send warning and leave
            await message.reply_text(
                "⚠️ **Unauthorized Group**

"
                "This bot can only operate in approved groups.
"
                "Contact the bot owner for approval.

"
                "Leaving group in 5 seconds...",
                parse_mode='Markdown'
            )
            
            await context.application.create_task(
                self._delayed_leave(context.bot, chat.id, 5)
            )
            
            logger.warning(f"Bot added to unapproved group {chat.id} by {added_by}")
            
        except Exception as e:
            logger.error(f"Error handling bot addition: {e}")
    
    async def _auto_approve_group(self, group_id: int, title: str, approved_by: int):
        """Auto-approve group"""
        await self.db.groups.update_one(
            {"group_id": group_id},
            {
                "$set": {
                    "group_id": group_id,
                    "group_title": title,
                    "approved": True,
                    "approved_by": approved_by,
                    "approved_at": datetime.utcnow(),
                    "added_at": datetime.utcnow()
                }
            },
            upsert=True
        )
    
    async def _delayed_leave(self, bot, chat_id: int, delay: int):
        """Leave group after delay"""
        import asyncio
        await asyncio.sleep(delay)
        try:
            await bot.leave_chat(chat_id)
            logger.info(f"Left unapproved group {chat_id}")
        except TelegramError as e:
            logger.error(f"Failed to leave group {chat_id}: {e}")
    
    async def approve_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Command: /approvegroup
        Main admin can approve groups
        """
        user_id = update.effective_user.id
        
        # Check if main admin
        if user_id != self.config.MAIN_ADMIN_ID:
            await update.message.reply_text("❌ Only the main admin can approve groups.")
            return
        
        chat = update.effective_chat
        
        if chat.type not in ['group', 'supergroup']:
            await update.message.reply_text(
                "❌ This command can only be used in groups."
            )
            return
        
        try:
            await self._auto_approve_group(chat.id, chat.title, user_id)
            
            await update.message.reply_text(
                "✅ **Group Approved!**

"
                "This group is now authorized to use the bot.
"
                "Users can send codes to search for files.",
                parse_mode='Markdown'
            )
            
            logger.info(f"Group {chat.id} approved by {user_id}")
            
        except Exception as e:
            logger.error(f"Group approval failed: {e}")
            await update.message.reply_text("❌ Failed to approve group.")
