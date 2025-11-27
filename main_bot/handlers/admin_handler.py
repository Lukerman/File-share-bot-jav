"""
Admin Handler - Complete admin panel for file management
Supports uploads, version control, admin management, and moderation
"""
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from datetime import datetime

from backend.crypto_utils import CryptoService
from handlers.request_handler import RequestHandler

logger = logging.getLogger(__name__)


class AdminHandler:
    """Complete admin panel and file management system"""
    
    def __init__(self, db, config):
        self.db = db
        self.config = config
        self.crypto = CryptoService()
        self.request_handler = RequestHandler(db, config)
        
    async def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        admin = await self.db.admins.find_one({"user_id": user_id})
        return admin is not None
    
    async def is_main_admin(self, user_id: int) -> bool:
        """Check if user is main admin"""
        return user_id == self.config.MAIN_ADMIN_ID
    
    async def show_admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show main admin panel"""
        user_id = update.effective_user.id
        
        if not await self.is_admin(user_id):
            await update.message.reply_text("❌ You don't have admin access.")
            return
        
        is_main = await self.is_main_admin(user_id)
        
        # Admin panel keyboard
        keyboard = [
            [
                InlineKeyboardButton("📊 Statistics", callback_data="admin_stats"),
                InlineKeyboardButton("📁 Manage Files", callback_data="admin_files")
            ],
            [
                InlineKeyboardButton("📮 Requests", callback_data="admin_requests"),
                InlineKeyboardButton("🔐 Tokens", callback_data="admin_tokens")
            ]
        ]
        
        if is_main:
            keyboard.extend([
                [
                    InlineKeyboardButton("👥 Manage Admins", callback_data="admin_admins"),
                    InlineKeyboardButton("🏢 Manage Groups", callback_data="admin_groups")
                ],
                [
                    InlineKeyboardButton("🚫 Banned Users", callback_data="admin_bans"),
                    InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings")
                ]
            ])
        
        await update.message.reply_text(
            "🔧 **Admin Control Panel**

"
            "Select an option below:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def handle_admin_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Route admin panel callbacks"""
        query = update.callback_query
        user_id = update.effective_user.id
        
        if not await self.is_admin(user_id):
            await query.answer("❌ Unauthorized", show_alert=True)
            return
        
        action = query.data.replace('admin_', '')
        
        handlers = {
            'stats': self._show_statistics,
            'files': self._show_files,
            'requests': self._show_requests,
            'tokens': self._show_tokens,
            'admins': self._show_admins,
            'groups': self._show_groups,
            'bans': self._show_bans,
            'settings': self._show_settings
        }
        
        handler = handlers.get(action)
        if handler:
            await handler(query, context)
        else:
            await query.answer("Unknown action")
    
    async def _show_statistics(self, query, context):
        """Show system statistics"""
        try:
            # Gather stats
            total_videos = await self.db.videos.count_documents({"active": True})
            total_requests = await self.db.requests.count_documents({})
            total_tokens = await self.db.tokens.count_documents({"used": False})
            total_users = await self.db.users.count_documents({})
            total_groups = await self.db.groups.count_documents({"approved": True})
            banned_users = await self.db.users.count_documents({"banned": True})
            
            # Total downloads
            pipeline = [
                {"$group": {"_id": None, "total": {"$sum": "$total_downloads"}}}
            ]
            result = await self.db.videos.aggregate(pipeline).to_list(1)
            total_downloads = result[0]['total'] if result else 0
            
            text = (
                f"📊 **System Statistics**

"
                f"📦 Active Resources: {total_videos}
"
                f"📮 Pending Requests: {total_requests}
"
                f"🎟️ Unused Tokens: {total_tokens}
"
                f"👥 Total Users: {total_users}
"
                f"🏢 Approved Groups: {total_groups}
"
                f"🚫 Banned Users: {banned_users}
"
                f"📥 Total Downloads: {total_downloads}

"
                f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
            )
            
            keyboard = [[
                InlineKeyboardButton("🔄 Refresh", callback_data="admin_stats"),
                InlineKeyboardButton("⬅️ Back", callback_data="admin_panel")
            ]]
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Stats display failed: {e}")
            await query.answer("❌ Error loading statistics", show_alert=True)
    
    async def _show_files(self, query, context):
        """Show file management options"""
        keyboard = [
            [
                InlineKeyboardButton("📋 List Files", callback_data="admin_list_files"),
                InlineKeyboardButton("🔍 Search File", callback_data="admin_search_file")
            ],
            [
                InlineKeyboardButton("🗑️ Delete File", callback_data="admin_delete_file"),
                InlineKeyboardButton("🔄 Rotate Secret", callback_data="admin_rotate_secret")
            ],
            [InlineKeyboardButton("⬅️ Back", callback_data="admin_panel")]
        ]
        
        await query.edit_message_text(
            "📁 **File Management**

Select an action:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def _show_requests(self, query, context):
        """Show pending requests"""
        try:
            requests = await self.db.requests.find().sort(
                "request_count", -1
            ).limit(10).to_list(10)
            
            if not requests:
                text = "📮 No pending requests."
            else:
                text = "📮 **Top Pending Requests**

"
                for req in requests:
                    expires_in = (req['expires_at'] - datetime.utcnow()).days
                    text += (
                        f"🔖 `{req['code']}` - "
                        f"👥 {req['request_count']} users "
                        f"(expires in {expires_in}d)
"
                    )
            
            keyboard = [[
                InlineKeyboardButton("🔄 Refresh", callback_data="admin_requests"),
                InlineKeyboardButton("⬅️ Back", callback_data="admin_panel")
            ]]
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Requests display failed: {e}")
            await query.answer("❌ Error loading requests", show_alert=True)
    
    async def _show_tokens(self, query, context):
        """Show token statistics"""
        try:
            total_tokens = await self.db.tokens.count_documents({})
            unused_tokens = await self.db.tokens.count_documents({"used": False})
            used_tokens = await self.db.tokens.count_documents({"used": True})
            
            # Recent token activity
            recent = await self.db.tokens.find(
                {"used": True}
            ).sort("used_at", -1).limit(5).to_list(5)
            
            text = (
                f"🎟️ **Token Management**

"
                f"Total: {total_tokens}
"
                f"✅ Used: {used_tokens}
"
                f"⏳ Unused: {unused_tokens}

"
            )
            
            if recent:
                text += "**Recent Usage:**
"
                for token_doc in recent:
                    used_at = token_doc['used_at'].strftime('%H:%M')
                    text += f"• {token_doc['resource_id']} by {token_doc.get('used_by', 'unknown')} at {used_at}
"
            
            keyboard = [[
                InlineKeyboardButton("🔄 Refresh", callback_data="admin_tokens"),
                InlineKeyboardButton("⬅️ Back", callback_data="admin_panel")
            ]]
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Token display failed: {e}")
            await query.answer("❌ Error loading tokens", show_alert=True)
    
    async def _show_admins(self, query, context):
        """Show admin management (main admin only)"""
        if not await self.is_main_admin(query.from_user.id):
            await query.answer("❌ Main admin only", show_alert=True)
            return
        
        try:
            admins = await self.db.admins.find().to_list(None)
            
            text = "👥 **Admin Management**

"
            for admin in admins:
                role = admin['role']
                username = admin.get('username', 'N/A')
                text += f"• {username} ({admin['user_id']}) - {role}
"
            
            keyboard = [[
                InlineKeyboardButton("➕ Add Admin", callback_data="admin_add_admin"),
                InlineKeyboardButton("➖ Remove Admin", callback_data="admin_remove_admin")
            ], [
                InlineKeyboardButton("⬅️ Back", callback_data="admin_panel")
            ]]
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Admin display failed: {e}")
            await query.answer("❌ Error loading admins", show_alert=True)
    
    async def _show_groups(self, query, context):
        """Show group management"""
        try:
            groups = await self.db.groups.find(
                {"approved": True}
            ).limit(10).to_list(10)
            
            text = "🏢 **Approved Groups**

"
            if not groups:
                text += "No approved groups."
            else:
                for group in groups:
                    title = group.get('group_title', 'Unknown')
                    text += f"• {title} ({group['group_id']})
"
            
            keyboard = [[
                InlineKeyboardButton("🔄 Refresh", callback_data="admin_groups"),
                InlineKeyboardButton("⬅️ Back", callback_data="admin_panel")
            ]]
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Groups display failed: {e}")
            await query.answer("❌ Error loading groups", show_alert=True)
    
    async def _show_bans(self, query, context):
        """Show banned users"""
        try:
            banned = await self.db.users.find(
                {"banned": True}
            ).limit(10).to_list(10)
            
            text = "🚫 **Banned Users**

"
            if not banned:
                text += "No banned users."
            else:
                for user in banned:
                    user_id = user['user_id']
                    reason = user.get('ban_reason', 'N/A')
                    ban_type = "Permanent" if not user.get('ban_until') else "Temporary"
                    text += f"• {user_id} - {ban_type}
  Reason: {reason}

"
            
            keyboard = [[
                InlineKeyboardButton("🔓 Unban User", callback_data="admin_unban"),
                InlineKeyboardButton("⬅️ Back", callback_data="admin_panel")
            ]]
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Bans display failed: {e}")
            await query.answer("❌ Error loading bans", show_alert=True)
    
    async def _show_settings(self, query, context):
        """Show system settings"""
        text = (
            f"⚙️ **System Settings**

"
            f"🕐 Message Delete Delay: {self.config.GROUP_MESSAGE_DELETE_DELAY}s
"
            f"📅 Request Expiry: {self.config.REQUEST_EXPIRY_DAYS} days
"
            f"🌐 Mini WebApp: {self.config.MINI_WEBAPP_URL}
"
        )
        
        keyboard = [[
            InlineKeyboardButton("⬅️ Back", callback_data="admin_panel")
        ]]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def handle_database_channel_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle file uploads in Database Channel
        Extract code and version from caption, store file_id
        """
        message = update.message or update.channel_post
        
        if not message:
            return
        
        # Verify it's from database channel
        if message.chat.id != self.config.DATABASE_CHANNEL_ID:
            return
        
        caption = message.caption or ""
        
        # Extract code and version from caption
        # Expected format: "CODE VERSION" or "CODE-123 v2" etc.
        match = re.match(r'([A-Z0-9-]+)s+(.+)', caption, re.IGNORECASE)
        
        if not match:
            logger.warning(f"Invalid caption format: {caption}")
            return
        
        code = match.group(1).upper()
        version_label = match.group(2).strip()
        
        # Get file info
        file_id = None
        file_type = None
        file_size = None
        file_name = None
        
        if message.document:
            file_id = message.document.file_id
            file_type = "document"
            file_size = message.document.file_size
            file_name = message.document.file_name
        elif message.video:
            file_id = message.video.file_id
            file_type = "video"
            file_size = message.video.file_size
            file_name = message.video.file_name or "video.mp4"
        elif message.audio:
            file_id = message.audio.file_id
            file_type = "audio"
            file_size = message.audio.file_size
            file_name = message.audio.file_name or "audio.mp3"
        
        if not file_id:
            logger.warning("No supported file type found")
            return
        
        try:
            # Check if resource exists
            video = await self.db.videos.find_one({"code": code})
            
            if not video:
                # Create new resource with per-file secret
                file_secret = self.crypto.generate_secret()
                
                await self.db.videos.insert_one({
                    "code": code,
                    "versions": [{
                        "version": version_label,
                        "file_id": file_id,
                        "file_type": file_type,
                        "file_size": file_size,
                        "file_name": file_name,
                        "uploaded_by": message.from_user.id if message.from_user else 0,
                        "uploaded_at": datetime.utcnow()
                    }],
                    "file_secret": file_secret,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "active": True,
                    "total_downloads": 0
                })
                
                logger.info(f"New resource created: {code} v{version_label}")
            else:
                # Add new version
                await self.db.videos.update_one(
                    {"code": code},
                    {
                        "$push": {
                            "versions": {
                                "version": version_label,
                                "file_id": file_id,
                                "file_type": file_type,
                                "file_size": file_size,
                                "file_name": file_name,
                                "uploaded_by": message.from_user.id if message.from_user else 0,
                                "uploaded_at": datetime.utcnow()
                            }
                        },
                        "$set": {"updated_at": datetime.utcnow()}
                    }
                )
                
                logger.info(f"Version added: {code} v{version_label}")
            
            # Fulfill pending requests
            fulfilled_count = await self.request_handler.fulfill_requests(code, context)
            
            # Confirmation message
            await message.reply_text(
                f"✅ **Upload Successful**

"
                f"🔖 Code: `{code}`
"
                f"📌 Version: {version_label}
"
                f"📦 Type: {file_type}
"
                f"👥 Fulfilled: {fulfilled_count} requests",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Upload processing failed: {e}")
            await message.reply_text(f"❌ Upload failed: {str(e)}")
