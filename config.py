#!/usr/bin/env python3
"""
IPM Library Telegram Bot - Configuration
"""

import os
import logging

# Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

# Admin User IDs (replace with actual admin Telegram user IDs)
ADMIN_IDS = [
    int(admin_id) for admin_id in os.getenv('ADMIN_IDS', '').split(',') 
    if admin_id.strip().isdigit()
]

# If no admin IDs from environment, use fallback (replace with actual admin IDs)
if not ADMIN_IDS:
    ADMIN_IDS = [123456789]  # Replace with actual admin Telegram user ID

# Channel ID for forwarding approved books (optional)
CHANNEL_ID = os.getenv('CHANNEL_ID', '')  # Channel username or ID like @ipm_library or -1001234567890

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Bot Settings
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB max file size
ALLOWED_FILE_TYPES = ['.pdf', '.doc', '.docx', '.txt', '.epub']

# Rate Limiting (submissions per user per day)
MAX_SUBMISSIONS_PER_DAY = 5

# Storage Settings
STORAGE_FILE = 'storage.json'
BACKUP_INTERVAL_HOURS = 24  # Create backup every 24 hours
CLEANUP_INTERVAL_DAYS = 90  # Clean old data every 90 days

# Message Templates
WELCOME_MESSAGE = """
🏛️ Welcome to IPM Library Bot!

📚 **How to submit a book:**
1. Send text in format: `Title | Author | Google Drive Link (optional)`
2. Or upload a PDF/document directly

📋 **Available commands:**
• /start - Show this welcome message
• /leaderboard - View weekly top contributors
• /help - Get detailed help

💡 **Admin commands** (admin only):
• /pending - Review pending book submissions
• /broadcast - Send message to all users

Happy reading! 📖
"""

ERROR_MESSAGES = {
    'invalid_format': "❌ Invalid format. Use: `Title | Author | Google Drive Link (optional)`",
    'empty_fields': "❌ Title and Author cannot be empty.",
    'file_too_large': "❌ File is too large. Maximum size is 50MB.",
    'unsupported_file': "❌ Unsupported file type. Please upload PDF, DOC, DOCX, TXT, or EPUB files.",
    'admin_only': "❌ This command is only available to administrators.",
    'unknown_command': "❌ Unknown command. Use /help to see available commands.",
    'rate_limit': "❌ You've reached the daily submission limit. Please try again tomorrow.",
    'general_error': "❌ An error occurred. Please try again later."
}

SUCCESS_MESSAGES = {
    'book_submitted': "✅ Book submitted successfully! Your submission has been sent for admin approval.",
    'book_approved': "✅ Book approved and added to library!",
    'book_rejected': "❌ Book rejected.",
    'broadcast_sent': "📤 Broadcast message sent successfully!"
}

# Validation Settings
MIN_TITLE_LENGTH = 1
MAX_TITLE_LENGTH = 200
MIN_AUTHOR_LENGTH = 1
MAX_AUTHOR_LENGTH = 100

def validate_config():
    """Validate configuration settings"""
    errors = []
    
    if not BOT_TOKEN or BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        errors.append("BOT_TOKEN is not set or using default value")
    
    if not ADMIN_IDS:
        errors.append("No admin IDs configured")
    
    if errors:
        logging.error("Configuration errors:")
        for error in errors:
            logging.error(f"  - {error}")
        return False
    
    return True

def get_bot_info():
    """Get bot configuration info for logging"""
    return {
        'bot_token_set': bool(BOT_TOKEN and BOT_TOKEN != 'YOUR_BOT_TOKEN_HERE'),
        'admin_count': len(ADMIN_IDS),
        'channel_configured': bool(CHANNEL_ID),
        'storage_file': STORAGE_FILE,
        'log_level': LOG_LEVEL
    }

# Environment-specific settings
if os.getenv('ENVIRONMENT') == 'development':
    LOG_LEVEL = 'DEBUG'
    MAX_SUBMISSIONS_PER_DAY = 10  # Allow more submissions in development

# Initialize logging with configured level
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT
)

# Validate configuration on import
if __name__ == "__main__":
    if validate_config():
        print("✅ Configuration is valid")
        info = get_bot_info()
        for key, value in info.items():
            print(f"  {key}: {value}")
    else:
        print("❌ Configuration has errors")
        exit(1)
