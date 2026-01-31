"""Main entry point for the Telegram tennis court booking bot."""
import logging
import re
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database import Database
from config import Config
from scheduler import BookingScheduler

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize components
db = Database()
config = Config()
bot_instance = None
scheduler = None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    welcome_message = """
🎾 Welcome to the Tennis Court Booking Bot!

Commands:
/book <date> <time> <duration> <court> - Request a booking
  Example: /book 2024-12-25 10:00 30 Court 1

/status - View your pending bookings
/cancel <id> - Cancel a pending booking

The bot will automatically process your requests at 7:00 AM, 48 hours in advance.
"""
    await update.message.reply_text(welcome_message)


async def book_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /book command to create a booking request."""
    if not config.is_configured():
        await update.message.reply_text(
            "❌ Bot is not fully configured. Please set up credentials in config.ini"
        )
        return
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "❌ Usage: /book <date> <time> [court]\n"
            "Example: /book 2024-12-25 10:00 Court 1"
        )
        return
    
    try:
        # Parse arguments
        date_str = context.args[0]
        time_str = context.args[1]
        # Extract duration from args[2] safely
        try:
            duration = int(context.args[2])
            # Everything after duration is the court preference
            court_preference = " ".join(context.args[3:]) if len(context.args) > 3 else None
        except ValueError:
            # Fallback: if args[2] isn't a number, assume duration is 90 and args[2:] is court
            duration = 90
            court_preference = " ".join(context.args[2:])

        # Validate date format (YYYY-MM-DD)
        date_pattern = r'^\d{4}-\d{2}-\d{2}$'
        if not re.match(date_pattern, date_str):
            await update.message.reply_text(
                "❌ Invalid date format. Please use YYYY-MM-DD (e.g., 2024-12-25)"
            )
            return
        
        # Validate date is in the future
        try:
            requested_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            if requested_date < datetime.now().date():
                await update.message.reply_text("❌ Cannot book dates in the past")
                return
        except ValueError:
            await update.message.reply_text("❌ Invalid date")
            return
        
        # Validate time format (HH:MM)
        time_pattern = r'^\d{2}:\d{2}$'
        if not re.match(time_pattern, time_str):
            await update.message.reply_text(
                "❌ Invalid time format. Please use HH:MM (e.g., 10:00)"
            )
            return
        
        # Add request to database
        user_id = str(update.effective_user.id)
        chat_id = str(update.effective_chat.id)
        request_id = db.add_request(
            user_id=user_id,
            chat_id=chat_id,
            requested_date=date_str,
            requested_time=time_str,
            court_preference=court_preference,
            duration=duration
        )
        
        court_text = f" (Court: {court_preference})" if court_preference else ""
        await update.message.reply_text(
            f"✅ Booking request #{request_id} created!\n"
            f"Date: {date_str}\n"
            f"Time: {time_str}{court_text}\n\n"
            f"Duration: {duration} minutes\n\n"
            f"The bot will attempt to book this at 7:00 AM, 48 hours in advance."
        )
        
        logger.info(f"User {user_id} created booking request #{request_id}")
        
    except Exception as e:
        logger.error(f"Error processing book command: {e}")
        await update.message.reply_text(f"❌ Error creating booking request: {str(e)}")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command to show pending bookings."""
    user_id = str(update.effective_user.id)
    requests = db.get_user_requests(user_id)
    
    if not requests:
        await update.message.reply_text("You have no booking requests.")
        return
    
    # Filter to show pending requests first
    pending = [r for r in requests if r['status'] == 'pending']
    completed = [r for r in requests if r['status'] == 'completed']
    failed = [r for r in requests if r['status'] == 'failed']
    
    message_parts = []
    
    if pending:
        message_parts.append("📋 Pending Requests:")
        for req in pending[:10]:  # Limit to 10 most recent
            court_text = f" (Court: {req['court_preference']})" if req['court_preference'] else ""
            message_parts.append(
                f"  #{req['id']}: {req['requested_date']} at {req['requested_time']}{court_text} for {req['duration']} minutes"
            )
    
    if completed:
        message_parts.append("\n✅ Completed:")
        for req in completed[:5]:
            message_parts.append(f"  #{req['id']}: {req['requested_date']} at {req['requested_time']}")
    
    if failed:
        message_parts.append("\n❌ Failed:")
        for req in failed[:5]:
            message_parts.append(f"  #{req['id']}: {req['requested_date']} at {req['requested_time']}")
    
    await update.message.reply_text("\n".join(message_parts) if message_parts else "No requests found.")


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cancel command to cancel a pending booking."""
    if not context.args or len(context.args) < 1:
        await update.message.reply_text("❌ Usage: /cancel <request_id>")
        return
    
    try:
        request_id = int(context.args[0])
        user_id = str(update.effective_user.id)
        
        if db.cancel_request(request_id, user_id):
            await update.message.reply_text(f"✅ Booking request #{request_id} cancelled.")
        else:
            await update.message.reply_text(
                f"❌ Could not cancel request #{request_id}. "
                "It may not exist, already be processed, or belong to another user."
            )
    except ValueError:
        await update.message.reply_text("❌ Invalid request ID. Please provide a number.")
    except Exception as e:
        logger.error(f"Error cancelling request: {e}")
        await update.message.reply_text(f"❌ Error cancelling request: {str(e)}")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors in the bot."""
    logger.error(f"Update {update} caused error {context.error}")


def main():
    """Main function to start the bot."""
    global bot_instance, scheduler
    
    # Check configuration
    if not config.is_configured():
        logger.error("Bot is not configured. Please set up config.ini with:")
        logger.error("  - Telegram bot token")
        logger.error("  - Booking website URL")
        logger.error("  - Booking website username and password")
        return
    
    # Initialize Telegram bot
    token = config.get_telegram_token()
    application = Application.builder().token(token).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("book", book_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    
    # Register error handler
    application.add_error_handler(error_handler)
    
    # Get bot instance for scheduler
    bot_instance = application.bot
    
    # Initialize and start scheduler
    scheduler = BookingScheduler(db, config, bot_instance)
    scheduler.start()
    
    logger.info("Bot starting...")
    
    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
