"""
Request Handler - Manages user requests for unavailable files
Supports request merging, expiry, and notification system
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RequestHandler:
    """Manages file request system"""
    
    def __init__(self, db, config):
        self.db = db
        self.config = config
        
    async def handle_request_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle request button click"""
        query = update.callback_query
        user_id = update.effective_user.id
        
        # Parse callback: request_CODE
        code = query.data.replace('request_', '')
        
        # Check if already requested by this user
        existing = await self.db.requests.find_one({
            "code": code.upper(),
            "requesters": user_id
        })
        
        if existing:
            await query.answer("✅ You've already requested this file!", show_alert=True)
            return
        
        # Add or update request
        result = await self.db.requests.update_one(
            {"code": code.upper()},
            {
                "$addToSet": {"requesters": user_id},
                "$inc": {"request_count": 1},
                "$setOnInsert": {
                    "created_at": datetime.utcnow(),
                    "expires_at": datetime.utcnow() + timedelta(days=self.config.REQUEST_EXPIRY_DAYS)
                }
            },
            upsert=True
        )
        
        # Get updated request
        request = await self.db.requests.find_one({"code": code.upper()})
        requester_count = request['request_count']
        
        # Send notification to request channel
        if result.upserted_id or requester_count == 1:
            # New request - send to channel
            await self._notify_request_channel(code, requester_count)
        else:
            # Updated existing request
            await self._update_request_channel_message(code, requester_count)
        
        await query.answer("✅ Request submitted!", show_alert=True)
        await query.edit_message_text(
            f"📮 **Request Submitted: {code}**

"
            f"👥 Total Requesters: {requester_count}

"
            f"You'll be notified when this file becomes available.
"
            f"Request expires in {self.config.REQUEST_EXPIRY_DAYS} days.",
            parse_mode='Markdown'
        )
        
        logger.info(f"User {user_id} requested {code} (total: {requester_count})")
    
    async def _notify_request_channel(self, code: str, count: int):
        """Send new request notification to channel"""
        try:
            text = (
                f"📮 **New File Request**

"
                f"🔖 Code: `{code}`
"
                f"👥 Requesters: {count}
"
                f"📅 Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

"
                f"Upload to Database Channel with caption: `{code} Version`"
            )
            
            message = await context.bot.send_message(
                chat_id=self.config.REQUEST_CHANNEL_ID,
                text=text,
                parse_mode='Markdown'
            )
            
            # Store message_id for future updates
            await self.db.requests.update_one(
                {"code": code.upper()},
                {"$set": {"channel_message_id": message.message_id}}
            )
            
        except Exception as e:
            logger.error(f"Failed to notify request channel: {e}")
    
    async def _update_request_channel_message(self, code: str, count: int):
        """Update existing request message in channel"""
        try:
            request = await self.db.requests.find_one({"code": code.upper()})
            message_id = request.get('channel_message_id')
            
            if not message_id:
                return
            
            text = (
                f"📮 **File Request (Updated)**

"
                f"🔖 Code: `{code}`
"
                f"👥 Requesters: {count} ⬆️
"
                f"📅 Updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

"
                f"Upload to Database Channel with caption: `{code} Version`"
            )
            
            await context.bot.edit_message_text(
                chat_id=self.config.REQUEST_CHANNEL_ID,
                message_id=message_id,
                text=text,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.debug(f"Could not update request message: {e}")
    
    async def fulfill_requests(self, code: str, context: ContextTypes.DEFAULT_TYPE):
        """
        Notify all requesters when file becomes available
        Called by admin upload handler
        """
        try:
            request = await self.db.requests.find_one({"code": code.upper()})
            
            if not request:
                return 0
            
            requesters = request.get('requesters', [])
            
            # Notify each requester
            success_count = 0
            for user_id in requesters:
                try:
                    keyboard = [[
                        InlineKeyboardButton(
                            "🔓 Get File",
                            callback_data=f"unlock_{code}_1"
                        )
                    ]]
                    
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=(
                            f"🎉 **Your Request is Ready!**

"
                            f"📦 Resource: `{code}`

"
                            f"The file you requested is now available.
"
                            f"Click below to unlock it!"
                        ),
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='Markdown'
                    )
                    success_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to notify user {user_id}: {e}")
            
            # Delete request entry
            await self.db.requests.delete_one({"code": code.upper()})
            
            # Update request channel message
            message_id = request.get('channel_message_id')
            if message_id:
                try:
                    await context.bot.edit_message_text(
                        chat_id=self.config.REQUEST_CHANNEL_ID,
                        message_id=message_id,
                        text=(
                            f"✅ **Request Fulfilled**

"
                            f"🔖 Code: `{code}`
"
                            f"👥 Notified: {success_count} users
"
                            f"📅 Fulfilled: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
                        ),
                        parse_mode='Markdown'
                    )
                except:
                    pass
            
            logger.info(f"Fulfilled request for {code}, notified {success_count} users")
            return success_count
            
        except Exception as e:
            logger.error(f"Request fulfillment failed: {e}")
            return 0
