"""
Configuration module - loads and validates environment variables.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)


class Config:
    """Application configuration loaded from environment variables."""

    # Telegram API credentials
    API_ID: int
    API_HASH: str

    # Bot for notifications (mentions)
    BOT_TOKEN: str
    NOTIFICATION_CHAT_ID: int

    # Session settings
    SESSION_NAME: str = "userbot_session"

    # Optional settings
    LOG_LEVEL: str = "INFO"
    IGNORED_CHATS: list = []
    IGNORE_BOTS: bool = True

    def __init__(self):
        """Load and validate configuration."""
        self._load_required()
        self._load_optional()
        self._validate()

    def _load_required(self):
        """Load required environment variables."""
        self.API_ID = os.getenv("API_ID")
        self.API_HASH = os.getenv("API_HASH")
        self.BOT_TOKEN = os.getenv("BOT_TOKEN")
        self.NOTIFICATION_CHAT_ID = os.getenv("NOTIFICATION_CHAT_ID")

    def _load_optional(self):
        """Load optional environment variables with defaults."""
        self.SESSION_NAME = os.getenv("SESSION_NAME", "userbot_session")
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        
        # Ignored chats (comma-separated list of IDs)
        ignored_chats_raw = os.getenv("IGNORED_CHATS", "")
        self.IGNORED_CHATS = []
        if ignored_chats_raw:
            for item in ignored_chats_raw.split(","):
                item = item.strip()
                if item:
                    try:
                        self.IGNORED_CHATS.append(int(item))
                    except ValueError:
                        pass

        # Ignore bots (default True)
        ignore_bots_raw = os.getenv("IGNORE_BOTS", "True")
        self.IGNORE_BOTS = ignore_bots_raw.lower() in ("true", "1", "yes", "on")

    def _validate(self):
        """Validate that all required variables are set."""
        errors = []

        # API ID
        if not self.API_ID:
            errors.append("API_ID is required")
        else:
            try:
                self.API_ID = int(self.API_ID)
            except ValueError:
                errors.append("API_ID must be an integer")

        # API Hash
        if not self.API_HASH:
            errors.append("API_HASH is required")

        # Notification Bot Token
        if not self.BOT_TOKEN:
            errors.append("BOT_TOKEN is required (get from @BotFather)")
        elif self.BOT_TOKEN == "your_bot_token":
            errors.append("BOT_TOKEN: please set your actual bot token")

        # Notification Chat ID
        if not self.NOTIFICATION_CHAT_ID:
            errors.append("NOTIFICATION_CHAT_ID is required (get from @userinfobot)")
        elif self.NOTIFICATION_CHAT_ID == "your_telegram_user_id":
            errors.append("NOTIFICATION_CHAT_ID: please set your actual Telegram ID")
        else:
            try:
                self.NOTIFICATION_CHAT_ID = int(self.NOTIFICATION_CHAT_ID)
            except ValueError:
                errors.append("NOTIFICATION_CHAT_ID must be an integer")

        if errors:
            print("Configuration errors:")
            for error in errors:
                print(f"   {error}")
            print("\nPlease update your .env file with correct values.")
            sys.exit(1)


# Global config instance
config = Config()
