"""
Help and Information Handler
Provides user documentation and command reference
"""
from telegram import Update
from telegram.ext import ContextTypes


class HelpHandler:
    """Provides help and documentation"""
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        text = (
            "👋 **Welcome to File Provider Bot!**

"
            "I help you find and download files using resource codes.

"
            "**Quick Start:**
"
            "• Send any code like ABC-123
"
            "• I'll search for the file
"
            "• Watch a short ad to unlock
"
            "• Get your file!

"
            "Use /help for detailed information."
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        text = (
            "📚 **Help & Documentation**

"
            
            "**🔍 How to Search:**
"
            "Simply send a resource code in any format:
"
            "• ABC-123
"
            "• ABC_123
"
            "• ABC123

"
            "I'll automatically detect and search for it.

"
            
            "**🎯 Lazy Search Mode:**
"
            "Made a typo? No problem!
"
            "I'll suggest similar codes if exact match isn't found.

"
            
            "**📮 Request System:**
"
            "File not available? Click 'Request' button.
"
            "You'll be notified when it's uploaded.
"
            "Requests expire after 7 days.

"
            
            "**🔓 Unlock Process:**
"
            "1. Find your file
"
            "2. Click 'Get File'
"
            "3. Watch rewarded ad (15-30 seconds)
"
            "4. Receive file automatically

"
            
            "**🎟️ Token System:**
"
            "• Tokens are permanent (no expiry)
"
            "• Single-use only
"
            "• Secure HMAC-signed
"
            "• Can regenerate if needed

"
            
            "**📤 File Delivery:**
"
            "After watching ad:
"
            "• Redirect to @FileBot
"
            "• Token verified automatically
"
            "• File sent instantly
"
            "• Can request more versions

"
            
            "**⚠️ Rules:**
"
            "• Max 3 codes per message
"
            "• No spam (progressive cooldowns)
"
            "• Rate limit: 10 requests/minute
"
            "• 5 warnings = 24h ban

"
            
            "**👨‍💼 Admin Commands:**
"
            "/adminpanel - Admin control panel
"
            "/approvegroup - Approve current group

"
            
            "**📞 Need Help?**
"
            "Contact admin if you experience issues."
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')
