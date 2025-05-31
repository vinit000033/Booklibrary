#!/usr/bin/env python3
"""
IPM Library Telegram Bot - Main Handler
"""

import telebot
import json
import os
import logging
from datetime import datetime, timedelta
from telebot import types
from utils import (
    load_storage, save_storage, add_user, add_book_submission,
    get_pending_books, approve_book, get_weekly_leaderboard,
    get_monthly_leaderboard, get_alltime_leaderboard,
    get_all_users, is_admin
)
from config import BOT_TOKEN, ADMIN_IDS, CHANNEL_ID

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start_command(message):
    """Handle /start command"""
    try:
        user_id = message.from_user.id
        username = message.from_user.username or "Unknown"
        first_name = message.from_user.first_name or "User"
        
        # Add user to storage
        add_user(user_id, username, first_name)
        
        welcome_text = f"""
🏛️ Welcome to IPM Library Bot, {first_name}!

📚 **How to submit a book:**
1. Send text in format: `Title | Author | Google Drive Link (optional)`
2. Or upload a PDF/document directly
3. Use the quick submit button below

📋 **Available commands:**
• /start - Show this welcome message
• /leaderboard - View weekly top contributors
• /help - Get detailed help

💡 **Admin commands** (admin only):
• /pending - Review pending book submissions
• /broadcast - Send message to all users

Happy reading! 📖
        """
        
        # Create inline keyboard for quick actions
        markup = types.InlineKeyboardMarkup(row_width=2)
        submit_btn = types.InlineKeyboardButton("📚 Submit Book", callback_data="submit_book")
        leaderboard_btn = types.InlineKeyboardButton("🏆 Leaderboard", callback_data="show_leaderboard")
        help_btn = types.InlineKeyboardButton("❓ Help", callback_data="show_help")
        stats_btn = types.InlineKeyboardButton("📊 Library Stats", callback_data="show_stats")
        markup.add(submit_btn, leaderboard_btn)
        markup.add(help_btn, stats_btn)
        
        bot.reply_to(message, welcome_text, parse_mode='Markdown', reply_markup=markup)
        logger.info(f"User {username} ({user_id}) started the bot")
        
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        bot.reply_to(message, "❌ An error occurred. Please try again later.")

@bot.message_handler(commands=['help'])
def help_command(message):
    """Handle /help command"""
    try:
        help_text = """
📚 **IPM Library Bot Help**

**Book Submission Methods:**
1. **Text Format:**
   Send: `Title | Author | Google Drive Link`
   Example: `1984 | George Orwell | https://drive.google.com/file/d/abc123/view`

2. **PDF Upload:**
   Simply upload a PDF file with an optional caption

**Google Drive Link Requirements:**
• Set file sharing to "Anyone with the link can view"
• Copy the full Google Drive URL
• Test your link in incognito mode before submitting
• The bot will automatically format your link correctly

**Commands:**
• `/start` - Welcome message
• `/help` - This help message
• `/leaderboard` - Weekly top contributors

**Admin Commands:**
• `/pending` - Review pending submissions
• `/broadcast <message>` - Send message to all users

**Notes:**
• All submissions require admin approval
• Approved books are shared in our library channel
• Google Drive links are optional but recommended
        """
        
        bot.reply_to(message, help_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in help command: {e}")
        bot.reply_to(message, "❌ An error occurred. Please try again later.")

@bot.message_handler(commands=['pending'])
def pending_command(message):
    """Handle /pending command - Admin only"""
    try:
        user_id = message.from_user.id
        
        if not is_admin(user_id):
            bot.reply_to(message, "❌ This command is only available to administrators.")
            return
        
        pending_books = get_pending_books()
        
        if not pending_books:
            bot.reply_to(message, "✅ No pending book submissions!")
            return
        
        for book in pending_books:
            # Create book info text
            book_info = f"""
📚 **Pending Book Submission**

**Title:** {book['title']}
**Author:** {book['author']}
**Submitted by:** @{book['submitter_username']} ({book['submitter_name']})
**Date:** {book['timestamp']}
"""
            
            if book.get('gdrive_link'):
                book_info += f"**Google Drive:** [Open Link]({book['gdrive_link']})\n"
                book_info += f"**Link Status:** {'✅ Validated' if 'usp=sharing' in book['gdrive_link'] else '⚠️ Check Access'}\n"
            
            if book.get('file_id'):
                book_info += f"**File:** Uploaded document\n"
            
            # Create inline keyboard for approval
            markup = types.InlineKeyboardMarkup()
            approve_btn = types.InlineKeyboardButton(
                "✅ Approve", 
                callback_data=f"approve_{book['id']}"
            )
            reject_btn = types.InlineKeyboardButton(
                "❌ Reject", 
                callback_data=f"reject_{book['id']}"
            )
            markup.add(approve_btn, reject_btn)
            
            # Send book info with approval buttons
            if book.get('file_id'):
                bot.send_document(
                    message.chat.id,
                    book['file_id'],
                    caption=book_info,
                    reply_markup=markup,
                    parse_mode='Markdown'
                )
            else:
                bot.send_message(
                    message.chat.id,
                    book_info,
                    reply_markup=markup,
                    parse_mode='Markdown'
                )
        
        logger.info(f"Admin {message.from_user.username} viewed pending books")
        
    except Exception as e:
        logger.error(f"Error in pending command: {e}")
        bot.reply_to(message, "❌ An error occurred while fetching pending books.")

def format_leaderboard(leaderboard, period_name, days):
    """Format leaderboard data for display"""
    if not leaderboard:
        return f"📊 No contributions in the {period_name.lower()} period yet!"
    
    period_text = f"{period_name} (Last {days} days)" if days else period_name
    leaderboard_text = f"🏆 **{period_text} Leaderboard**\n\n"
    
    for i, (user, count) in enumerate(leaderboard, 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📚"
        leaderboard_text += f"{emoji} **{i}.** {user['name']} (@{user['username']}) - {count} book(s)\n"
    
    return leaderboard_text

@bot.message_handler(commands=['leaderboard'])
def leaderboard_command(message):
    """Handle /leaderboard command"""
    try:
        weekly_leaderboard = get_weekly_leaderboard()
        
        # Create inline keyboard for leaderboard options
        markup = types.InlineKeyboardMarkup(row_width=2)
        weekly_btn = types.InlineKeyboardButton("📅 Weekly", callback_data="leaderboard_weekly")
        monthly_btn = types.InlineKeyboardButton("📆 Monthly", callback_data="leaderboard_monthly")
        all_time_btn = types.InlineKeyboardButton("🏆 All Time", callback_data="leaderboard_alltime")
        refresh_btn = types.InlineKeyboardButton("🔄 Refresh", callback_data="leaderboard_refresh")
        markup.add(weekly_btn, monthly_btn)
        markup.add(all_time_btn, refresh_btn)
        
        # Show weekly leaderboard by default
        leaderboard_text = format_leaderboard(weekly_leaderboard, "Weekly", 7)
        
        bot.reply_to(message, leaderboard_text, parse_mode='Markdown', reply_markup=markup)
        logger.info(f"User {message.from_user.username} viewed leaderboard")
        
    except Exception as e:
        logger.error(f"Error in leaderboard command: {e}")
        bot.reply_to(message, "❌ An error occurred while fetching leaderboard.")

@bot.message_handler(commands=['broadcast'])
def broadcast_command(message):
    """Handle /broadcast command - Admin only"""
    try:
        user_id = message.from_user.id
        
        if not is_admin(user_id):
            bot.reply_to(message, "❌ This command is only available to administrators.")
            return
        
        # Extract message to broadcast
        command_parts = message.text.split(' ', 1)
        if len(command_parts) < 2:
            bot.reply_to(message, "❌ Usage: /broadcast <message>")
            return
        
        broadcast_message = command_parts[1]
        users = get_all_users()
        
        if not users:
            bot.reply_to(message, "❌ No users found to broadcast to.")
            return
        
        success_count = 0
        failed_count = 0
        
        # Send broadcast message to all users
        for user in users:
            try:
                bot.send_message(user['id'], f"📢 **Broadcast Message**\n\n{broadcast_message}", parse_mode='Markdown')
                success_count += 1
            except Exception as e:
                logger.warning(f"Failed to send broadcast to user {user['id']}: {e}")
                failed_count += 1
        
        result_text = f"📤 Broadcast completed!\n✅ Sent to: {success_count} users\n❌ Failed: {failed_count} users"
        bot.reply_to(message, result_text)
        
        logger.info(f"Admin {message.from_user.username} sent broadcast to {success_count} users")
        
    except Exception as e:
        logger.error(f"Error in broadcast command: {e}")
        bot.reply_to(message, "❌ An error occurred while broadcasting.")

@bot.callback_query_handler(func=lambda call: call.data.startswith(('approve_', 'reject_', 'submit_book', 'show_leaderboard', 'show_help', 'show_stats', 'leaderboard_')))
def handle_approval_callback(call):
    """Handle approval/rejection callbacks and user interface actions"""
    try:
        user_id = call.from_user.id
        
        # Handle user interface buttons
        if call.data == 'submit_book':
            submit_text = """
📚 **Submit a Book to IPM Library**

Choose one of these methods:

**Method 1 - Text Format:**
Send a message like: `Title | Author | Google Drive Link (optional)`
Example: `1984 | George Orwell | https://drive.google.com/file/d/abc123/view`

**Important for Google Drive links:**
• Make sure your file is set to "Anyone with the link can view"
• Share the full Google Drive link (the bot will automatically format it correctly)
• Test your link in an incognito browser to ensure it works

**Method 2 - File Upload:**
Upload a PDF/document with optional caption

Start typing your book submission now!
            """
            bot.edit_message_text(
                submit_text,
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown'
            )
            bot.answer_callback_query(call.id, "Ready to receive your book submission!")
            return
        
        elif call.data == 'show_leaderboard':
            leaderboard_command(call.message)
            bot.answer_callback_query(call.id)
            return
        
        # Handle leaderboard period selection
        elif call.data.startswith('leaderboard_'):
            period = call.data.split('_')[1]
            leaderboard_text = ""
            
            if period == 'weekly':
                leaderboard = get_weekly_leaderboard()
                leaderboard_text = format_leaderboard(leaderboard, "Weekly", 7)
            elif period == 'monthly':
                leaderboard = get_monthly_leaderboard()
                leaderboard_text = format_leaderboard(leaderboard, "Monthly", 30)
            elif period == 'alltime':
                leaderboard = get_alltime_leaderboard()
                leaderboard_text = format_leaderboard(leaderboard, "All Time", None)
            elif period == 'refresh':
                # Refresh current view (default to weekly)
                leaderboard = get_weekly_leaderboard()
                leaderboard_text = format_leaderboard(leaderboard, "Weekly", 7)
            else:
                # Default fallback
                leaderboard = get_weekly_leaderboard()
                leaderboard_text = format_leaderboard(leaderboard, "Weekly", 7)
            
            # Create the same inline keyboard
            markup = types.InlineKeyboardMarkup(row_width=2)
            weekly_btn = types.InlineKeyboardButton("📅 Weekly", callback_data="leaderboard_weekly")
            monthly_btn = types.InlineKeyboardButton("📆 Monthly", callback_data="leaderboard_monthly")
            all_time_btn = types.InlineKeyboardButton("🏆 All Time", callback_data="leaderboard_alltime")
            refresh_btn = types.InlineKeyboardButton("🔄 Refresh", callback_data="leaderboard_refresh")
            markup.add(weekly_btn, monthly_btn)
            markup.add(all_time_btn, refresh_btn)
            
            bot.edit_message_text(
                leaderboard_text,
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown',
                reply_markup=markup
            )
            bot.answer_callback_query(call.id, f"📊 {period.title()} leaderboard updated!")
            return
        
        elif call.data == 'show_help':
            help_command(call.message)
            bot.answer_callback_query(call.id)
            return
        
        elif call.data == 'show_stats':
            from utils import get_library_stats
            stats = get_library_stats()
            stats_text = f"""
📊 **IPM Library Statistics**

📚 Total Books: {stats.get('total_books', 0)}
👥 Total Users: {stats.get('total_users', 0)}
⏳ Pending Submissions: {stats.get('pending_submissions', 0)}

🏆 Most Active Contributor: {stats.get('most_active_user', {}).get('name', 'None yet')} ({stats.get('most_active_user', {}).get('contributions', 0)} books)
            """
            bot.edit_message_text(
                stats_text,
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown'
            )
            bot.answer_callback_query(call.id)
            return
        
        # Handle admin approval/rejection actions
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ Only administrators can approve books.")
            return
        
        action, book_id = call.data.split('_', 1)
        
        if action == 'approve':
            success, book_data = approve_book(book_id)
            
            if success and book_data:
                # Edit the message to show approval
                bot.edit_message_reply_markup(
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=None
                )
                
                # Add approval status to the message
                approved_text = f"{call.message.text}\n\n✅ **APPROVED** by @{call.from_user.username}"
                
                try:
                    bot.edit_message_text(
                        approved_text,
                        call.message.chat.id,
                        call.message.message_id,
                        parse_mode='Markdown'
                    )
                except:
                    # If editing fails (e.g., for documents), send a new message
                    bot.send_message(
                        call.message.chat.id,
                        f"✅ Book approved by @{call.from_user.username}",
                        reply_to_message_id=call.message.message_id
                    )
                
                # Forward to channel if configured
                if CHANNEL_ID:
                    try:
                        channel_text = f"""
📚 **New Book Added to Library**

**Title:** {book_data['title']}
**Author:** {book_data['author']}
**Contributed by:** @{book_data['submitter_username']}
"""
                        
                        if book_data.get('gdrive_link'):
                            channel_text += f"**Google Drive:** {book_data['gdrive_link']}"
                        
                        if book_data.get('file_id'):
                            bot.send_document(
                                CHANNEL_ID,
                                book_data['file_id'],
                                caption=channel_text,
                                parse_mode='Markdown'
                            )
                        else:
                            bot.send_message(CHANNEL_ID, channel_text, parse_mode='Markdown')
                        
                        logger.info(f"Book '{book_data['title']}' forwarded to channel")
                        
                    except Exception as e:
                        logger.error(f"Error forwarding to channel: {e}")
                
                bot.answer_callback_query(call.id, "✅ Book approved and added to library!")
                logger.info(f"Admin {call.from_user.username} approved book: {book_data['title']}")
                
            else:
                bot.answer_callback_query(call.id, "❌ Error approving book.")
        
        elif action == 'reject':
            # Handle rejection (remove from pending)
            storage = load_storage()
            storage['books'] = [book for book in storage['books'] if book['id'] != book_id]
            save_storage(storage)
            
            # Edit message to show rejection
            bot.edit_message_reply_markup(
                call.message.chat.id,
                call.message.message_id,
                reply_markup=None
            )
            
            rejected_text = f"{call.message.text}\n\n❌ **REJECTED** by @{call.from_user.username}"
            
            try:
                bot.edit_message_text(
                    rejected_text,
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='Markdown'
                )
            except:
                bot.send_message(
                    call.message.chat.id,
                    f"❌ Book rejected by @{call.from_user.username}",
                    reply_to_message_id=call.message.message_id
                )
            
            bot.answer_callback_query(call.id, "❌ Book rejected.")
            logger.info(f"Admin {call.from_user.username} rejected book ID: {book_id}")
    
    except Exception as e:
        logger.error(f"Error in approval callback: {e}")
        bot.answer_callback_query(call.id, "❌ An error occurred.")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    """Handle document uploads (PDF submissions)"""
    try:
        user_id = message.from_user.id
        username = message.from_user.username or "Unknown"
        first_name = message.from_user.first_name or "User"
        
        # Add user to storage
        add_user(user_id, username, first_name)
        
        # Get document info
        document = message.document
        file_id = document.file_id
        file_name = document.file_name or "Unknown"
        
        # Extract title and author from caption or filename
        title = ""
        author = ""
        gdrive_link = ""
        
        if message.caption:
            # Try to parse caption as Title | Author | Link format
            parts = [part.strip() for part in message.caption.split('|')]
            if len(parts) >= 2:
                title = parts[0]
                author = parts[1]
                if len(parts) >= 3:
                    gdrive_link = parts[2]
            else:
                title = message.caption
                author = "Unknown"
        else:
            # Use filename as title
            title = file_name.replace('.pdf', '').replace('.doc', '').replace('.docx', '')
            author = "Unknown"
        
        # Add book submission
        book_id = add_book_submission(
            title=title,
            author=author,
            submitter_id=user_id,
            submitter_username=username,
            submitter_name=first_name,
            gdrive_link=gdrive_link,
            file_id=file_id
        )
        
        success_message = f"""
✅ **Book submitted successfully!**

📚 **Title:** {title}
👤 **Author:** {author}
📁 **File:** {file_name}

Your submission has been sent for admin approval. You'll be notified once it's reviewed!
        """
        
        bot.reply_to(message, success_message, parse_mode='Markdown')
        logger.info(f"User {username} submitted document: {title}")
        
    except Exception as e:
        logger.error(f"Error handling document: {e}")
        bot.reply_to(message, "❌ An error occurred while processing your document. Please try again.")

@bot.message_handler(func=lambda message: True)
def handle_text_submission(message):
    """Handle text messages (book submissions in Title | Author | Link format)"""
    try:
        # Skip if message starts with / (command)
        if message.text.startswith('/'):
            bot.reply_to(message, "❌ Unknown command. Use /help to see available commands.")
            return
        
        user_id = message.from_user.id
        username = message.from_user.username or "Unknown"
        first_name = message.from_user.first_name or "User"
        
        # Add user to storage
        add_user(user_id, username, first_name)
        
        # Parse the message for book submission format
        text = message.text.strip()
        
        # Check if it contains the pipe separator
        if '|' not in text:
            help_text = """
❓ **How to submit a book:**

**Method 1 - Text Format:**
Send: `Title | Author | Google Drive Link (optional)`
Example: `1984 | George Orwell | https://drive.google.com/file/d/abc123/view`

**Method 2 - File Upload:**
Upload a PDF/document with optional caption

**Google Drive Tips:**
• Set sharing to "Anyone with the link can view"
• Test your link in incognito mode first
• The bot will automatically format your link

Use /help for more information.
            """
            bot.reply_to(message, help_text, parse_mode='Markdown')
            return
        
        # Parse the submission
        parts = [part.strip() for part in text.split('|')]
        
        if len(parts) < 2:
            bot.reply_to(message, "❌ Invalid format. Use: `Title | Author | Google Drive Link (optional)`", parse_mode='Markdown')
            return
        
        title = parts[0]
        author = parts[1]
        gdrive_link = parts[2] if len(parts) >= 3 else ""
        
        # Validate title and author
        if not title or not author:
            bot.reply_to(message, "❌ Title and Author cannot be empty.")
            return
        
        # Add book submission
        book_id = add_book_submission(
            title=title,
            author=author,
            submitter_id=user_id,
            submitter_username=username,
            submitter_name=first_name,
            gdrive_link=gdrive_link
        )
        
        success_message = f"""
✅ **Book submitted successfully!**

📚 **Title:** {title}
👤 **Author:** {author}
"""
        
        if gdrive_link:
            success_message += f"🔗 **Link:** {gdrive_link}\n"
        
        success_message += "\nYour submission has been sent for admin approval. You'll be notified once it's reviewed!"
        
        bot.reply_to(message, success_message, parse_mode='Markdown')
        logger.info(f"User {username} submitted book: {title} by {author}")
        
    except Exception as e:
        logger.error(f"Error handling text submission: {e}")
        bot.reply_to(message, "❌ An error occurred while processing your submission. Please try again.")

def main():
    """Main function to start the bot"""
    try:
        logger.info("Starting IPM Library Bot...")
        
        # Initialize storage file if it doesn't exist
        if not os.path.exists('storage.json'):
            initial_storage = {
                "users": [],
                "books": []
            }
            save_storage(initial_storage)
            logger.info("Created initial storage.json file")
        
        logger.info("Bot is running and ready to receive messages...")
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise

if __name__ == "__main__":
    main()
