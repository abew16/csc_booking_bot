"""Configuration management for credentials and settings."""
import configparser
import os
from pathlib import Path


class Config:
    def __init__(self, config_file: str = "config.ini"):
        """Initialize configuration from file or environment variables."""
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self._load_config()
    
    def _load_config(self):
        """Load configuration from file if it exists."""
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
        else:
            # Create default structure
            self.config['TELEGRAM'] = {}
            self.config['BOOKING'] = {}
            self._save_config()
    
    def _save_config(self):
        """Save configuration to file."""
        with open(self.config_file, 'w') as f:
            self.config.write(f)
    
    def get_telegram_token(self) -> str:
        """Get Telegram bot token from config or environment."""
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if token:
            return token
        return self.config.get('TELEGRAM', 'bot_token', fallback='')
    
    def get_booking_url(self) -> str:
        """Get booking website URL from config or environment."""
        url = os.getenv('BOOKING_URL')
        if url:
            return url
        return self.config.get('BOOKING', 'url', fallback='')
    
    def get_username(self) -> str:
        """Get booking website username from config or environment."""
        username = os.getenv('BOOKING_USERNAME')
        if username:
            return username
        return self.config.get('BOOKING', 'username', fallback='')
    
    def get_password(self) -> str:
        """Get booking website password from config or environment."""
        password = os.getenv('BOOKING_PASSWORD')
        if password:
            return password
        return self.config.get('BOOKING', 'password', fallback='')
    
    def set_telegram_token(self, token: str):
        """Set Telegram bot token."""
        if 'TELEGRAM' not in self.config:
            self.config['TELEGRAM'] = {}
        self.config['TELEGRAM']['bot_token'] = token
        self._save_config()
    
    def set_booking_credentials(self, url: str, username: str, password: str):
        """Set booking website credentials."""
        if 'BOOKING' not in self.config:
            self.config['BOOKING'] = {}
        self.config['BOOKING']['url'] = url
        self.config['BOOKING']['username'] = username
        self.config['BOOKING']['password'] = password
        self._save_config()
    
    def is_configured(self) -> bool:
        """Check if all required configuration is present."""
        return bool(
            self.get_telegram_token() and
            self.get_booking_url() and
            self.get_username() and
            self.get_password()
        )
