"""
Base notifier interface.
"""

from abc import ABC, abstractmethod
from typing import Optional


class BaseNotifier(ABC):
    """Abstract base class for all notification services."""

    @abstractmethod
    async def send_notification(
        self,
        text: str,
        message_link: Optional[str] = None,
        parse_mode: str = "HTML",
    ) -> bool:
        """
        Send notification message.

        Args:
            text: Message text
            message_link: Optional link to the original message
            parse_mode: Parse mode (HTML or Markdown)

        Returns:
            True if message was sent successfully
        """
        pass

    @abstractmethod
    async def send_mention_alert(
        self,
        sender_name: str,
        sender_username: Optional[str],
        chat_title: str,
        message_text: str,
        message_link: Optional[str] = None,
        mention_type: str = "упомянул",
        tag: str = "mention",
    ) -> bool:
        """
        Send formatted mention alert.
        """
        pass

    @abstractmethod
    async def close(self):
        """Close any open connections/sessions."""
        pass

    @staticmethod
    def build_message_link(chat_id: int, message_id: int, is_private: bool = False) -> str:
        """
        Build a link to a Telegram message.
        """
        if is_private:
            return f"tg://openmessage?user_id={chat_id}&message_id={message_id}"

        if chat_id < 0:
            chat_id_str = str(chat_id)
            if chat_id_str.startswith("-100"):
                link_chat_id = chat_id_str[4:]
            else:
                link_chat_id = chat_id_str[1:]
            return f"https://t.me/c/{link_chat_id}/{message_id}"

        return f"tg://openmessage?user_id={chat_id}&message_id={message_id}"
