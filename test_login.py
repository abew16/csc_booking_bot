import logging
import time
from booking_scraper import BookingScraper
from config import Config

# Configure logging to see the decision-making process
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def test_full_booking_flow():
    config = Config()
    
    # Target details for the test
    TEST_DATE = "2026-02-02"
    TEST_TIME = "12:30"
    TEST_COURT = "Outdoor Court 4"
    TEST_DURATION = 60

    scraper = BookingScraper(
        url=config.get_booking_url(),
        username=config.get_username(),
        password=config.get_password(),
        headless=True # Keep browser visible for debugging. Set to True for production.
    )
    
    try:
        logging.info("Step 1: Attempting Login...")
        if not scraper.login():
            logging.error("Login failed. Check your credentials and selectors.")
            return

        logging.info(f"Step 2: Navigating to Booking for {TEST_DATE}...")
        # Note: make_booking handles the navigation and interaction 
        result = scraper.make_booking(
            date=TEST_DATE,
            time_slot=TEST_TIME,
            court_preference=TEST_COURT,
            duration_minutes=TEST_DURATION
        )
        
        if result['success']:
            logging.info(f"✅ Success: {result['message']}")
        else:
            logging.error(f"❌ Failed: {result['message']}")
            
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
    finally:
        logging.info("Test complete. Keeping browser open for 15 seconds for inspection...")
        time.sleep(15)
        scraper.close()

if __name__ == "__main__":
    test_full_booking_flow()