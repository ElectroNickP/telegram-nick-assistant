"""
Notification bot - sends alerts via Telegram Bot API.
"""

import logging
import aiohttp
from typing import Optional
from .base import BaseNotifier

logger = logging.getLogger(__name__)


class NotificationBot(BaseNotifier):
    """Bot for sending notification messages via Telegram Bot API."""

    BASE_URL = "https://api.telegram.org/bot{token}/{method}"

    def __init__(self, bot_token: str, chat_id: int):
        """
        Initialize notification bot.

        Args:
            bot_token: Bot token from @BotFather
            chat_id: Target chat ID for notifications
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _api_call(self, method: str, **params) -> dict:
        """
        Make API call to Telegram Bot API.

        Args:
            method: API method name
            **params: Method parameters

        Returns:
            API response as dict
        """
        url = self.BASE_URL.format(token=self.bot_token, method=method)
        session = await self._get_session()

        try:
            async with session.post(url, json=params) as response:
                result = await response.json()

                if not result.get("ok"):
                    logger.error("Bot API error: %s", result.get("description"))

                return result
        except Exception as e:
            logger.error("Failed to call Bot API: %s", e)
            return {"ok": False, "error": str(e)}

    async def send_notification(
        self,
        text: str,
        message_link: Optional[str] = None,
        parse_mode: str = "HTML",
        reply_markup: Optional[dict] = None,
    ) -> bool:
        """
        Send notification message.

        Args:
            text: Message text (supports HTML formatting)
            message_link: Optional link to the original message
            parse_mode: Parse mode (HTML or Markdown)
            reply_markup: Optional reply markup (keyboard)

        Returns:
            True if message was sent successfully
        """
        params = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }

        # Use explicitly provided reply_markup or compile one from message_link
        if reply_markup:
            params["reply_markup"] = reply_markup
        elif message_link:
            params["reply_markup"] = {
                "inline_keyboard": [[
                    {"text": "📍 Перейти к сообщению", "url": message_link}
                ]]
            }

        result = await self._api_call("sendMessage", **params)
        return result.get("ok", False)

    def get_main_menu(self) -> dict:
        """Get the main menu reply keyboard."""
        return {
            "keyboard": [
                [{"text": "📊 Отчет по лодкам"}],
                [{"text": "📖 Дневник капитана"}, {"text": "📆 Мои записи"}],
            ],
            "resize_keyboard": True,
            "one_time_keyboard": False
        }

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

        Args:
            sender_name: Name of the person who mentioned
            sender_username: Username of the sender (without @)
            chat_title: Title of the chat where mention occurred
            message_text: Text of the message
            message_link: Link to the message
            mention_type: Type of mention (упомянул, ответил, etc.)
            tag: Hashtag for filtering: "reply" or "mention"

        Returns:
            True if alert was sent successfully
        """
        sender_info = sender_name
        if sender_username:
            sender_info += f" (@{sender_username})"

        max_text_length = 500
        if len(message_text) > max_text_length:
            message_text = message_text[:max_text_length] + "..."

        message_text = self._escape_html(message_text)

        # Hashtag at top for easy filtering (reply vs mention)
        hashtag = f"#{tag}"

        # Short title by type
        if tag == "reply":
            title = "Ответ на ваше сообщение"
        else:
            title = "Упоминание"

        text = (
            f"{hashtag}\n\n"
            f"<b>{title}</b>\n\n"
            f"👤 <b>От:</b> {sender_info}\n"
            f"💬 <b>Чат:</b> {chat_title}\n\n"
            f"<b>Сообщение:</b>\n"
            f"<i>{message_text}</i>"
        )

        return await self.send_notification(text, message_link)

    @staticmethod
    def _escape_html(text: str) -> str:
        """Escape HTML special characters."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    async def close(self):
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.debug("NotificationBot session closed")
