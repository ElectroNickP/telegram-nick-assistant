"""
Modular rules for detecting mentions and replies in messages.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Tuple
from telethon.events import NewMessage
from telethon.tl.types import (
    MessageEntityMention,
    MessageEntityMentionName,
)
from telethon.utils import get_inner_text

logger = logging.getLogger(__name__)


class BaseRule(ABC):
    """Abstract base class for mention detection rules."""

    @abstractmethod
    async def check(self, event: NewMessage.Event, my_id: int, my_username: Optional[str]) -> Optional[Tuple[str, str]]:
        """
        Check if the message matches the rule.

        Returns:
            (display_type, tag) if matched, else None.
        """
        pass


class ReplyRule(BaseRule):
    """Rule for detecting replies to the user's messages."""

    async def check(self, event: NewMessage.Event, my_id: int, my_username: Optional[str]) -> Optional[Tuple[str, str]]:
        message = event.message
        if message.reply_to:
            try:
                replied_msg = await event.get_reply_message()
                if replied_msg and replied_msg.sender_id == my_id:
                    return ("ответил на ваше сообщение", "reply")
            except Exception as e:
                logger.warning("ReplyRule: не удалось загрузить reply-сообщение: %s", e)
        return None


class UsernameMentionRule(BaseRule):
    """Rule for detecting @username mentions."""

    async def check(self, event: NewMessage.Event, my_id: int, my_username: Optional[str]) -> Optional[Tuple[str, str]]:
        if not my_username:
            return None

        message = event.message
        if not message.entities:
            return None

        raw_text = getattr(message, "message", None) or getattr(message, "text", None) or ""
        if not isinstance(raw_text, str):
            raw_text = ""
        my_username_lower = my_username.lower()

        for entity in message.entities:
            if isinstance(entity, MessageEntityMention):
                try:
                    # Telegram offsets are in UTF-16 code units.
                    # Convert string to UTF-16-LE bytes to slice safely by UTF-16 code unit index.
                    encoded = raw_text.encode('utf-16-le')
                    start = entity.offset * 2
                    end = (entity.offset + entity.length) * 2
                    mentioned_username = encoded[start:end].decode('utf-16-le')
                    mentioned_username = mentioned_username.strip().lstrip("@").lower()
                    
                    if mentioned_username == my_username_lower:
                        return ("упомянул вас", "mention")
                except Exception as e:
                    logger.warning("UsernameMentionRule extraction error: %s", e)
        
        return None


class IDMentionRule(BaseRule):
    """Rule for detecting mentions by User ID (text links)."""

    async def check(self, event: NewMessage.Event, my_id: int, my_username: Optional[str]) -> Optional[Tuple[str, str]]:
        message = event.message
        if not message.entities:
            return None

        for entity in message.entities:
            if isinstance(entity, MessageEntityMentionName):
                if entity.user_id == my_id:
                    return ("упомянул вас", "mention")
        
        return None
