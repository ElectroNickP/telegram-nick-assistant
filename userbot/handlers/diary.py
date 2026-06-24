import logging
from typing import TYPE_CHECKING, Optional
import datetime
import asyncio
from telethon import events
from telethon.tl.types import MessageMediaDocument, DocumentAttributeVideo

if TYPE_CHECKING:
    from userbot.client import UserbotClient
    from userbot.storage import BoatStorage
    from notifier.base import BaseNotifier

logger = logging.getLogger(__name__)


class DiaryHandler:
    """Handler for Captain's Diary features (recording videos and viewing history)."""

    def __init__(
        self,
        userbot: "UserbotClient",
        notifier: "BaseNotifier",
        storage: "BoatStorage"
    ):
        self.userbot = userbot
        self.notifier = notifier
        self.storage = storage

        # Determine bot's user ID from token to monitor messages in the bot's PM
        bot_token = getattr(self.notifier, "bot_token", "")
        self.bot_id = int(bot_token.split(":")[0]) if ":" in bot_token else None

    def register(self):
        """Register the event handlers for diary."""
        if not self.bot_id:
            logger.error("DiaryHandler could not determine bot ID, will not register.")
            return

        self.userbot.client.add_event_handler(
            self._on_message,
            events.NewMessage(chats=[self.bot_id, getattr(self.notifier, "chat_id", None)])
        )
        logger.info("DiaryHandler registered.")

    async def _on_message(self, event: events.NewMessage.Event):
        """Handle diary commands and video notes sent to the bot."""
        message = event.message
        text = message.text or ""
        
        # We process outgoing messages (since it's in bot's PM) or commands
        
        # 1. Menu Buttons
        if text.strip() == "📖 Дневник капитана":
            await self._send_diary_welcome()
            return
            
        if text.strip() == "📆 Мои записи":
            await self._send_diary_history()
            return

        # 2. Receiving Video Note (Кружок)
        # It's considered an outgoing message if user sends it directly to the bot.
        if message.out or getattr(message, 'sender_id', None) == self.userbot.my_id:
            if message.media and isinstance(message.media, MessageMediaDocument):
                document = message.media.document
                # Check if document has a Video attribute and it specifies 'round_message'
                for attr in document.attributes:
                    if isinstance(attr, DocumentAttributeVideo) and getattr(attr, 'round_message', False):
                        await self._process_video_note(message)
                        return

    async def _send_diary_welcome(self):
        """Send instructions to record a daily video."""
        text = (
            "📖 <b>Дневник капитана</b>\n\n"
            "Чтобы зафиксировать сегодняшний день, просто отправьте мне <b>видео-сообщение (кружок)</b> прямо в этот чат.\n\n"
            "Я бережно сохраню его в бортовой журнал! ⚓️"
        )
        await self.notifier.send_notification(text)

    async def _send_diary_history(self):
        """Show recent diary entries with links to messages."""
        entries = self.storage.get_recent_diary_entries(limit=10)
        
        if not entries:
            await self.notifier.send_notification("📭 В бортовом журнале пока нет записей.")
            return

        lines = ["📆 <b>Архив бортового журнала:</b>\n"]
        
        for entry in entries:
            # Format date beautifully (e.g. 21 апреля, 19:30)
            try:
                dt = datetime.datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=datetime.timezone.utc)
                local_dt = dt + datetime.timedelta(hours=7) # Phuket time
                date_str = local_dt.strftime("%d.%m.%Y, %H:%M")
            except Exception:
                date_str = str(entry['timestamp'])[:16]

            message_id = entry['message_id']
            # We use notifier's build_message_link method
            link = self.notifier.build_message_link(self.bot_id, message_id, is_private=True)
            
            lines.append(f"• <b>{date_str}</b> — <a href='{link}'>Смотреть запись 📹</a>")

        await self.notifier.send_notification(
            "\n".join(lines),
            reply_markup=self.notifier.get_main_menu()
        )

    async def _process_video_note(self, message):
        """Save the video note to the DB and confirm."""
        self.storage.log_diary_entry(
            message_id=message.id,
            timestamp=message.date
        )
        
        # Artificial small delay to make it feel natural
        await asyncio.sleep(1)
        
        # Reply to user via bot
        await self.notifier.send_notification("✅ <b>Дневник сохранён!</b> Отличного отдыха, капитан! 🚢")
