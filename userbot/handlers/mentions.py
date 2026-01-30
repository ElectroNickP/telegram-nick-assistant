"""
Mention handler - detects when user is mentioned or replied to.
"""

import logging
from typing import TYPE_CHECKING
from telethon import events
from telethon.tl.types import (
    MessageEntityMention,
    MessageEntityMentionName,
    User,
)

if TYPE_CHECKING:
    from notifier.bot import NotificationBot
    from userbot.client import UserbotClient

logger = logging.getLogger(__name__)


class MentionHandler:
    """Handler for detecting mentions and replies to the user."""

    def __init__(self, userbot: "UserbotClient", notifier: "NotificationBot"):
        """
        Initialize mention handler.

        Args:
            userbot: UserbotClient instance
            notifier: NotificationBot instance for sending alerts
        """
        self.userbot = userbot
        self.notifier = notifier
        self._my_id: int = None
        self._my_username: str = None

    def register(self):
        """Register event handler with the client."""
        self.userbot.client.add_event_handler(
            self._on_new_message,
            events.NewMessage(incoming=True),
        )
        logger.info("MentionHandler registered")

    async def _on_new_message(self, event: events.NewMessage.Event):
        """
        Handle incoming messages and check for mentions.

        Args:
            event: New message event
        """
        if self._my_id is None:
            self._my_id = self.userbot.my_id
            self._my_username = self.userbot.my_username

        message = event.message

        if message.sender_id == self._my_id:
            return

        if not message.text and not message.raw_text:
            return

        result = await self._check_mention(event)

        if result:
            mention_type, tag = result
            await self._send_alert(event, mention_type, tag)

    async def _check_mention(self, event: events.NewMessage.Event) -> tuple[str, str] | None:
        """
        Check if message contains a mention of the user.

        Args:
            event: New message event

        Returns:
            (display_type, tag) for notification, or None. tag: "reply" | "mention"
        """
        message = event.message

        if message.reply_to:
            try:
                replied_msg = await event.get_reply_message()
                if replied_msg and replied_msg.sender_id == self._my_id:
                    return ("ответил на ваше сообщение", "reply")
            except Exception as e:
                logger.debug("Could not get reply message: %s", e)

        if message.entities:
            text = message.text or message.raw_text or ""
            for entity in message.entities:
                if isinstance(entity, MessageEntityMention):
                    mentioned_username = text[entity.offset : entity.offset + entity.length]
                    mentioned_username = mentioned_username.lstrip("@").lower()
                    if self._my_username and mentioned_username == self._my_username.lower():
                        return ("упомянул вас", "mention")

                elif isinstance(entity, MessageEntityMentionName):
                    if entity.user_id == self._my_id:
                        return ("упомянул вас", "mention")

        return None

    async def _send_alert(self, event: events.NewMessage.Event, mention_type: str, tag: str):
        """
        Send notification about the mention.

        Args:
            event: New message event
            mention_type: Type of mention
        """
        message = event.message

        try:
            sender = await event.get_sender()
            sender_name = self._get_display_name(sender)
            sender_username = getattr(sender, "username", None)

            chat = await event.get_chat()
            chat_title = self._get_chat_title(chat)

            chat_id = event.chat_id
            is_private = isinstance(chat, User)
            message_link = self.notifier.build_message_link(
                chat_id,
                message.id,
                is_private,
            )

            message_text = message.text or message.raw_text or "[медиа-сообщение]"

            success = await self.notifier.send_mention_alert(
                sender_name=sender_name,
                sender_username=sender_username,
                chat_title=chat_title,
                message_text=message_text,
                message_link=message_link,
                mention_type=mention_type,
                tag=tag,
            )

            if success:
                logger.info("Notification sent: %s in %s", mention_type, chat_title)
            else:
                logger.error("Failed to send notification for mention in %s", chat_title)

        except Exception as e:
            logger.error("Error sending mention alert: %s", e, exc_info=True)

    @staticmethod
    def _get_display_name(entity) -> str:
        """Get display name for user/chat."""
        if isinstance(entity, User):
            parts = []
            if entity.first_name:
                parts.append(entity.first_name)
            if entity.last_name:
                parts.append(entity.last_name)
            return " ".join(parts) if parts else "Unknown User"

        if hasattr(entity, "title"):
            return entity.title

        return "Unknown"

    @staticmethod
    def _get_chat_title(chat) -> str:
        """Get chat title or name."""
        if isinstance(chat, User):
            parts = []
            if chat.first_name:
                parts.append(chat.first_name)
            if chat.last_name:
                parts.append(chat.last_name)
            name = " ".join(parts) if parts else "Unknown"
            return f"ЛС с {name}"

        if hasattr(chat, "title"):
            return chat.title

        return "Unknown Chat"


def create_mention_handler(userbot: "UserbotClient", notifier: "NotificationBot") -> MentionHandler:
    """
    Factory function to create and register mention handler.

    Args:
        userbot: UserbotClient instance
        notifier: NotificationBot instance

    Returns:
        MentionHandler instance
    """
    handler = MentionHandler(userbot, notifier)
    handler.register()
    return handler
