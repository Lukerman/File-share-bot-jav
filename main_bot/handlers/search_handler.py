"""
Search Handler - Code detection, lazy search, and unlock flow
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime
import asyncio

from utils.code_detector import CodeDetector
from utils.lazy_search import LazySearchEngine
from utils.spam_protection import SpamProtection
from backend.token_service import TokenService

logger = logging.getLogger(__name__)


class SearchHandler:
    """Handles code search and file unlock operations"""
    
    def __init__(self, db, config):
        self.db = db
        self.config = config
        self.detector = CodeDetector()
        self.search_engine = LazySearchEngine(db)
        self.spam_protection = SpamProtection(db)
        self.token_service = TokenService(db)
        
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle incoming messages - detect codes and search
        """
        message = update.message
        chat = message.chat
        user_id = update.effective_user.id
        
        # Check if in approved group or private chat
        if chat.type in ['group', 'supergroup']:
            group = await self.db.groups.find_one({"group_id": chat.id})
            if not group or not group.get('approved'):
                return  # Ignore messages in unapproved groups
        
        # Spam protection check
        allowed, reason = await self.spam_protection.check_user_permission(user_id)
        if not allowed:
            reply = await message.reply_text(f"⚠️ {reason}")
            if chat.type in ['group', 'supergroup']:
                await self._schedule_delete(reply, self.config.GROUP_MESSAGE_DELETE_DELAY)
            return
        
        # Rate limiting
        if not await self.spam_protection.check_rate_limit(user_id):
            warning = await self.spam_protection.issue_warning(user_id, "Rate limit exceeded")
            reply = await message.reply_text(
                f"⚠️ Too many requests! Please slow down.
"
                f"Cooldown: {warning.get('cooldown', 60)} seconds"
            )
            if chat.type in ['group', 'supergroup']:
                await self._schedule_delete(reply, self.config.GROUP_MESSAGE_DELETE_DELAY)
            return
        
        # Extract codes
        codes = self.detector.extract_codes(message.text)
        
        if not codes:
            return  # No codes found, ignore
        
        if len(codes) > CodeDetector.MAX_CODES_PER_MESSAGE:
            reply = await message.reply_text(
                f"⚠️ Too many codes detected!
"
                f"Please send maximum {CodeDetector.MAX_CODES_PER_MESSAGE} codes per message."
            )
            if chat.type in ['group', 'supergroup']:
                await self._schedule_delete(reply, self.config.GROUP_MESSAGE_DELETE_DELAY)
            return
        
        # Search for each code
        for code in codes:
            await self._process_code_search(code, message, context)
        
        # Update user activity
        await self.db.users.update_one(
            {"user_id": user_id},
            {
                "$set": {"last_activity": datetime.utcnow()},
                "$inc": {"total_requests": 1}
            },
            upsert=True
        )
    
    async def _process_code_search(self, code: str, message, context):
        """Process individual code search"""
        chat = message.chat
        
        # Smart search: exact + fuzzy
        exact_match, suggestions = await self.search_engine.smart_search(code)
        
        if exact_match:
            # Exact match found
            await self._send_exact_match_result(code, exact_match, message)
        elif suggestions:
            # Fuzzy matches found
            await self._send_fuzzy_suggestions(code, suggestions, message)
        else:
            # Not found - offer to request
            await self._send_not_found(code, message)
        
        # Schedule deletion for group messages
        if chat.type in ['group', 'supergroup']:
            await self._schedule_delete(message, self.config.GROUP_MESSAGE_DELETE_DELAY)
    
    async def _send_exact_match_result(self, code: str, video: dict, message):
        """Send exact match result with action buttons"""
        versions = video.get('versions', [])
        latest_version = versions[-1] if versions else None
        
        if not latest_version:
            await message.reply_text(f"❌ Resource {code} has no available versions.")
            return
        
        text = (
            f"✅ **Resource Found: {code}**

"
            f"📦 Available Versions: {len(versions)}
"
            f"📌 Latest: v{latest_version['version']}
"
        )
        
        if video.get('description'):
            text += f"
📝 {video['description']}"
        
        keyboard = [
            [
                InlineKeyboardButton("📄 View Details", callback_data=f"view_{code}"),
                InlineKeyboardButton("🔓 Get File", callback_data=f"unlock_{code}_{latest_version['version']}")
            ]
        ]
        
        reply = await message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        if message.chat.type in ['group', 'supergroup']:
            await self._schedule_delete(reply, self.config.GROUP_MESSAGE_DELETE_DELAY)
    
    async def _send_fuzzy_suggestions(self, code: str, suggestions: list, message):
        """Send fuzzy search suggestions"""
        text = f"🔍 **No exact match for '{code}'**

Did you mean:

"
        
        keyboard = []
        for suggestion in suggestions[:3]:
            match_code = suggestion['code']
            score = suggestion['score']
            text += f"• {match_code} (Match: {score}%)
"
            keyboard.append([
                InlineKeyboardButton(
                    f"📄 {match_code}",
                    callback_data=f"view_{match_code}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("❌ Not Found - Request It", callback_data=f"request_{code}")
        ])
        
        reply = await message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        if message.chat.type in ['group', 'supergroup']:
            await self._schedule_delete(reply, self.config.GROUP_MESSAGE_DELETE_DELAY)
    
    async def _send_not_found(self, code: str, message):
        """Send not found message with request option"""
        keyboard = [[
            InlineKeyboardButton("📮 Request This File", callback_data=f"request_{code}")
        ]]
        
        reply = await message.reply_text(
            f"❌ **Resource '{code}' not found.**

"
            f"Would you like to request it?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        if message.chat.type in ['group', 'supergroup']:
            await self._schedule_delete(reply, self.config.GROUP_MESSAGE_DELETE_DELAY)
    
    async def handle_view_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle 'View Details' button click"""
        query = update.callback_query
        code = query.data.replace('view_', '')
        
        video = await self.db.videos.find_one({"code": code})
        
        if not video:
            await query.edit_message_text("❌ Resource no longer available.")
            return
        
        versions = video.get('versions', [])
        text = (
            f"📦 **Resource: {code}**

"
            f"📌 Total Versions: {len(versions)}
"
            f"📥 Total Downloads: {video.get('total_downloads', 0)}

"
        )
        
        if video.get('description'):
            text += f"📝 Description: {video['description']}

"
        
        text += "**Available Versions:**
"
        for v in versions[-5:]:  # Show last 5 versions
            text += f"• v{v['version']} - {v.get('file_name', 'File')}
"
        
        keyboard = []
        for v in versions[-3:]:  # Buttons for last 3 versions
            keyboard.append([
                InlineKeyboardButton(
                    f"🔓 Get v{v['version']}",
                    callback_data=f"unlock_{code}_{v['version']}"
                )
            ])
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def handle_unlock(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle 'Get File' button - generate token and open Mini WebApp
        """
        query = update.callback_query
        user_id = update.effective_user.id
        
        # Parse callback data: unlock_CODE_VERSION
        parts = query.data.split('_')
        if len(parts) < 3:
            await query.edit_message_text("❌ Invalid request.")
            return
        
        code = parts[1]
        version = parts[2]
        
        # Find video and version
        video = await self.db.videos.find_one({"code": code})
        
        if not video:
            await query.edit_message_text("❌ Resource no longer available.")
            return
        
        # Get file_secret
        file_secret = video.get('file_secret')
        if not file_secret:
            await query.edit_message_text("❌ System error: missing secret.")
            logger.error(f"Missing file_secret for {code}")
            return
        
        # Generate token
        token = await self.token_service.generate_token(code, version, file_secret)
        
        if not token:
            await query.edit_message_text("❌ Failed to generate unlock token.")
            return
        
        # Create Mini WebApp URL
        webapp_url = f"{self.config.MINI_WEBAPP_URL}?t={token}"
        
        keyboard = [[
            InlineKeyboardButton("🎬 Watch Ad & Unlock", web_app={"url": webapp_url})
        ]]
        
        await query.edit_message_text(
            f"🔐 **Unlock {code} v{version}**

"
            f"Click the button below to watch a rewarded ad.
"
            f"After completion, you'll receive your file!",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        logger.info(f"Token generated for {code} v{version} by user {user_id}")
    
    async def handle_regenerate_token(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle token regeneration request"""
        query = update.callback_query
        
        # Extract resource info from context (stored during delivery)
        resource_data = context.user_data.get('last_delivery')
        
        if not resource_data:
            await query.answer("❌ No recent delivery found.", show_alert=True)
            return
        
        code = resource_data['code']
        version = resource_data['version']
        
        # Get file secret
        video = await self.db.videos.find_one({"code": code})
        if not video:
            await query.answer("❌ Resource no longer available.", show_alert=True)
            return
        
        # Generate new token
        token = await self.token_service.generate_token(
            code,
            version,
            video['file_secret']
        )
        
        if not token:
            await query.answer("❌ Failed to generate token.", show_alert=True)
            return
        
        webapp_url = f"{self.config.MINI_WEBAPP_URL}?t={token}"
        
        keyboard = [[
            InlineKeyboardButton("🎬 Watch Ad & Unlock", web_app={"url": webapp_url})
        ]]
        
        await query.edit_message_text(
            f"🔄 **New Token Generated**

"
            f"Click below to unlock {code} v{version}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def _schedule_delete(self, message, delay: int):
        """Schedule message deletion after delay"""
        async def delete_later():
            await asyncio.sleep(delay)
            try:
                await message.delete()
            except Exception as e:
                logger.debug(f"Failed to delete message: {e}")
        
        asyncio.create_task(delete_later())
