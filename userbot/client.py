"""
Telethon client initialization and management.
"""

import logging
from pathlib import Path
from telethon import TelegramClient

logger = logging.getLogger(__name__)


class UserbotClient:
    """Wrapper for Telethon TelegramClient with convenient initialization."""

    def __init__(self, api_id: int, api_hash: str, session_name: str = "userbot_session"):
        """
        Initialize userbot client.

        Args:
            api_id: Telegram API ID
            api_hash: Telegram API Hash
            session_name: Name for session file (stored in project root)
        """
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_name = session_name

        # Session file will be stored in project root
        session_path = Path(__file__).parent.parent / session_name

        self.client = TelegramClient(
            str(session_path),
            api_id,
            api_hash,
            system_version="4.16.30-vxCUSTOM",
        )

        self._me = None

    async def start(self):
        """Start the client and authenticate if needed."""
        logger.info("Starting userbot client...")
        await self.client.start()

        self._me = await self.client.get_me()
        logger.info("Logged in as: %s (@%s)", self._me.first_name, self._me.username)
        logger.info("User ID: %s", self._me.id)

        return self

    @property
    def me(self):
        """Get current user info."""
        return self._me

    @property
    def my_id(self) -> int:
        """Get current user ID."""
        return self._me.id if self._me else None

    @property
    def my_username(self) -> str:
        """Get current username (without @)."""
        return self._me.username if self._me else None

    def add_handler(self, handler, event):
        """Add event handler to the client."""
        self.client.add_event_handler(handler, event)
        logger.debug("Added handler: %s", handler.__name__)

    async def run_until_disconnected(self):
        """Run the client until disconnected."""
        logger.info("Userbot is running. Press Ctrl+C to stop.")
        await self.client.run_until_disconnected()

    async def disconnect(self):
        """Disconnect the client."""
        logger.info("Disconnecting userbot client...")
        await self.client.disconnect()


def create_client(api_id: int, api_hash: str, session_name: str = "userbot_session") -> UserbotClient:
    """
    Factory function to create userbot client.

    Args:
        api_id: Telegram API ID
        api_hash: Telegram API Hash
        session_name: Name for session file

    Returns:
        UserbotClient instance
    """
    return UserbotClient(api_id, api_hash, session_name)
