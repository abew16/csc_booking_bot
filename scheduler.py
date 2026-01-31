"""Task scheduler for processing booking requests at 7am daily."""
import schedule
import time
import threading
import logging
from datetime import datetime, timedelta
from database import Database
from booking_scraper import BookingScraper
from config import Config
from telegram import Bot

logger = logging.getLogger(__name__)


class BookingScheduler:
    def __init__(self, db: Database, config: Config, bot: Bot):
        """Initialize the scheduler with database, config, and Telegram bot."""
        self.db = db
        self.config = config
        self.bot = bot
        self.running = False
        self.thread = None
    
    def process_pending_requests(self):
        """Process all pending requests that are exactly 48 hours in advance."""
        logger.info("Processing pending booking requests...")
        
        # Calculate target date (2 days from today, since bookings open 48h in advance at 7am)
        # If today is Dec 23, we process requests for Dec 25
        target_date_obj = datetime.now().date() + timedelta(days=2)
        target_date = target_date_obj.strftime('%Y-%m-%d')
        
        # Get all pending requests for this date
        requests = self.db.get_requests_for_date(target_date)
        
        if not requests:
            logger.info(f"No pending requests for {target_date}")
            return
        
        logger.info(f"Found {len(requests)} pending request(s) for {target_date}")
        
        # Initialize scraper
        scraper = BookingScraper(
            url=self.config.get_booking_url(),
            username=self.config.get_username(),
            password=self.config.get_password(),
            headless=True
        )
        
        try:
            # Login once for all bookings
            if not scraper.login():
                error_msg = "Failed to login to booking website"
                logger.error(error_msg)
                # Notify all users about login failure
                for req in requests:
                    self.db.update_request_status(req['id'], 'failed', error_msg)
                    try:
                        self.bot.send_message(
                            chat_id=req['chat_id'],
                            text=f"❌ Booking request #{req['id']} failed: {error_msg}"
                        )
                    except Exception as e:
                        logger.error(f"Failed to send notification: {e}")
                return
            
            # Process each request
            for req in requests:
                try:
                    logger.info(f"Processing request #{req['id']}: {req['requested_date']} at {req['requested_time']}")
                    
                    result = scraper.make_booking(
                        date=req['requested_date'],
                        time_slot=req['requested_time'],
                        court_preference=req.get('court_preference'),
                        duration_minutes=req.get('duration', 90)
                    )
                    
                    # Update request status
                    status = 'completed' if result['success'] else 'failed'
                    self.db.update_request_status(req['id'], status, result['message'])
                    
                    # Send notification to user
                    emoji = "✅" if result['success'] else "❌"
                    message = f"{emoji} Booking request #{req['id']}: {result['message']}"
                    
                    try:
                        self.bot.send_message(chat_id=req['chat_id'], text=message)
                    except Exception as e:
                        logger.error(f"Failed to send notification to {req['chat_id']}: {e}")
                    
                    # Small delay between bookings
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error processing request #{req['id']}: {e}")
                    self.db.update_request_status(req['id'], 'failed', f'Error: {str(e)}')
                    try:
                        self.bot.send_message(
                            chat_id=req['chat_id'],
                            text=f"❌ Booking request #{req['id']} failed: {str(e)}"
                        )
                    except Exception as notify_error:
                        logger.error(f"Failed to send error notification: {notify_error}")
        
        finally:
            scraper.close()
        
        logger.info("Finished processing booking requests")
    
    def start(self):
        """Start the scheduler in a background thread."""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        # Schedule the job to run daily at 7:00 AM
        schedule.every().day.at("07:00").do(self.process_pending_requests)
        
        self.running = True
        
        def run_scheduler():
            logger.info("Scheduler started - will process requests daily at 7:00 AM")
            while self.running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        
        self.thread = threading.Thread(target=run_scheduler, daemon=True)
        self.thread.start()
        logger.info("Scheduler thread started")
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False
        schedule.clear()
        logger.info("Scheduler stopped")
    
    def trigger_now(self):
        """Manually trigger processing of pending requests (for testing)."""
        logger.info("Manually triggering request processing...")
        self.process_pending_requests()
