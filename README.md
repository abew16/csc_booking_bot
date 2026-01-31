# Tennis Court Booking Bot

A Telegram bot that automatically reserves tennis court time at your local club. The bot stores your booking requests and processes them automatically at 7:00 AM, 48 hours in advance.

## Features

- **Telegram Integration**: Chat with the bot via Telegram to request bookings
- **Automatic Processing**: Bot processes all pending requests daily at 7:00 AM
- **48-Hour Advance Booking**: Automatically books exactly 48 hours in advance
- **Court Preferences**: Specify your preferred court when making requests
- **Status Tracking**: Check the status of your booking requests anytime

## Setup

### Prerequisites

- Python 3.8 or higher
- Chrome browser (for Selenium web automation)
- ChromeDriver (compatible with your Chrome version)
- A Telegram bot token (get one from [@BotFather](https://t.me/botfather))

### Installation

1. Clone or download this repository

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install ChromeDriver:
   - Download from [ChromeDriver downloads](https://chromedriver.chromium.org/downloads)
   - Make sure it's in your PATH or in the same directory as the script
   - Alternatively, use `webdriver-manager` (add to requirements.txt if needed)

4. Configure the bot:
   - Copy `config.ini` and fill in your credentials:
     - `bot_token`: Your Telegram bot token from @BotFather
     - `url`: Your tennis club's booking website URL
     - `username`: Your login username
     - `password`: Your login password

## Usage

### Starting the Bot

Run the bot:
```bash
python main.py
```

The bot will:
- Start listening for Telegram messages
- Begin the daily scheduler (runs at 7:00 AM)
- Process pending requests automatically

### Telegram Commands

- `/start` - Get started and see available commands
- `/book <date> <time> [court]` - Create a booking request
  - Example: `/book 2024-12-25 10:00 Court 1`
  - Date format: YYYY-MM-DD
  - Time format: HH:MM
- `/status` - View all your booking requests
- `/cancel <id>` - Cancel a pending booking request

### How It Works

1. You send a booking request via Telegram (e.g., `/book 2024-12-25 10:00 Court 1`)
2. The bot stores your request in the database
3. Every morning at 7:00 AM, the bot:
   - Checks for requests that are exactly 48 hours in advance
   - Logs into the booking website
   - Attempts to make the bookings
   - Sends you a notification with the result

## Customization

### Website Selectors

The web scraper uses common CSS selectors to find login and booking elements. You may need to customize the selectors in `booking_scraper.py` to match your specific tennis club's website structure.

Key areas to customize:
- Login form selectors (username, password, submit button)
- Date picker selectors
- Time slot selectors
- Court selection selectors
- Success/error message detection

### Scheduler Time

To change the processing time from 7:00 AM, edit `scheduler.py`:
```python
schedule.every().day.at("07:00").do(self.process_pending_requests)
```

## Troubleshooting

### Bot Not Responding

- Check that your Telegram bot token is correct in `config.ini`
- Ensure the bot is running and has internet connection
- Check logs for error messages

### Booking Failures

- Verify your login credentials are correct
- Check that the website URL is correct
- The website structure may have changed - you may need to update selectors in `booking_scraper.py`
- Check logs for detailed error messages

### ChromeDriver Issues

- Ensure ChromeDriver version matches your Chrome browser version
- Make sure ChromeDriver is in your PATH or same directory
- On Windows, you may need to add ChromeDriver to your PATH

## Security Notes

- Never commit `config.ini` to version control (it's in `.gitignore`)
- Keep your credentials secure
- Consider using environment variables for production deployments

## License

This project is provided as-is for personal use.
