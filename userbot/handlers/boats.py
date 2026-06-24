"""
Boat status handler - detects boat reporting messages and logs them.
"""

import logging
import re
from typing import TYPE_CHECKING
from telethon import events

if TYPE_CHECKING:
    from userbot.client import UserbotClient
    from .storage import BoatStorage

logger = logging.getLogger(__name__)


class BoatHandler:
    """Handler for detecting and parsing boat status messages."""

    # Even more robust patterns
    BOAT_PATTERN = re.compile(
        r"Boat\s*:\s*(?P<boat>.+?)\s+Status\s*:\s*(?P<status>.+?)(?=\n|$)", 
        re.IGNORECASE
    )
    PIER_PATTERN = re.compile(r"Pier\s*:\s*(?P<pier>.+?)(?=\s+Program:|Boat:|Status:|$|\n)", re.IGNORECASE)
    PROGRAM_PATTERN = re.compile(r"Program\s*:\s*(?P<program>.+?)(?=\s+Boat:|Status:|$|\n)", re.IGNORECASE)

    def __init__(self, userbot: "UserbotClient", storage: "BoatStorage"):
        """
        Initialize boat handler.

        Args:
            userbot: UserbotClient instance
            storage: BoatStorage instance
        """
        self.userbot = userbot
        self.storage = storage
        self.monitored_chats = [-1003046226070, -1003338122569]

    def register(self):
        """Register event handler with the client."""
        self.userbot.client.add_event_handler(
            self._on_new_message,
            events.NewMessage(chats=self.monitored_chats),
        )
        logger.info("BoatHandler registered for chats: %s", self.monitored_chats)

    def _parse_text(self, text: str):
        """Helper to parse boat info from text."""
        if not text:
            return None
            
        # Standardize whitespace and remove non-breaking spaces
        text = text.replace('\xa0', ' ').replace('\r\n', '\n')
        
        match = self.BOAT_PATTERN.search(text)
        if match:
            boat_name = match.group("boat").strip()
            status = match.group("status").strip()
            
            # Extract optional fields
            pier_match = self.PIER_PATTERN.search(text)
            pier = pier_match.group("pier").strip() if pier_match else None
            
            program_match = self.PROGRAM_PATTERN.search(text)
            program = program_match.group("program").strip() if program_match else None
            
            return {
                "boat_name": boat_name,
                "status": status,
                "pier": pier,
                "program": program
            }
        return None

    async def scan_history(self, limit: int = 1000):
        """Scan last 24 hours of monitored chats to backfill data."""
        import datetime
        logger.info("Scanning history for boat updates (limit=%s)...", limit)
        now = datetime.datetime.now(datetime.timezone.utc)
        cutoff = now - datetime.timedelta(hours=24)
        
        count = 0
        for chat_id in self.monitored_chats:
            try:
                # Use offset_date for faster date-based scanning
                async for message in self.userbot.client.iter_messages(chat_id, limit=limit, offset_date=now):
                    if message.date < cutoff:
                        break
                        
                    data = self._parse_text(message.text)
                    if data:
                        self.storage.log_event(
                            **data,
                            chat_id=chat_id,
                            message_id=message.id,
                            timestamp=message.date
                        )
                        count += 1
            except Exception as e:
                logger.error("Error scanning history for chat %s: %s", chat_id, e)
        
        logger.info("History scan complete. Found %s boat updates.", count)

    async def _on_new_message(self, event: events.NewMessage.Event):
        """
        Handle incoming messages in monitored chats.
        """
        text = event.message.text
        if not text:
            return

        data = self._parse_text(text)
        if data:
            logger.info("Detected boat update: %s -> %s", data['boat_name'], data['status'])
            self.storage.log_event(
                **data,
                chat_id=event.chat_id,
                message_id=event.message.id
            )
