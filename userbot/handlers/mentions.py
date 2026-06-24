import logging
from typing import TYPE_CHECKING, List, Optional
from telethon import events
from telethon.tl.types import User

from config import config
from .rules import ReplyRule, UsernameMentionRule, IDMentionRule, BaseRule

if TYPE_CHECKING:
    from notifier.base import BaseNotifier
    from userbot.client import UserbotClient
    from ..storage import BoatStorage

logger = logging.getLogger(__name__)


class MentionHandler:
    """Handler for detecting mentions, replies, and boat report commands."""

    def __init__(
        self, 
        userbot: "UserbotClient", 
        notifier: "BaseNotifier",
        boat_storage: Optional["BoatStorage"] = None
    ):
        """
        Initialize mention handler.

        Args:
            userbot: UserbotClient instance
            notifier: BaseNotifier instance for sending alerts
            boat_storage: Optional BoatStorage for boat reports
        """
        self.userbot = userbot
        self.notifier = notifier
        self.boat_storage = boat_storage
        self._my_id: int = None
        self._my_username: str = None
        
        # Initialize rules
        self.rules: List[BaseRule] = [
            ReplyRule(),
            UsernameMentionRule(),
            IDRule := IDMentionRule(),
        ]

    def register(self):
        """Register event handler with the client."""
        # Detect both incoming and outgoing messages to catch commands from other devices
        self.userbot.client.add_event_handler(
            self._on_new_message,
            events.NewMessage(),
        )
        logger.info("MentionHandler registered with %s rules", len(self.rules))

    async def _on_new_message(self, event: events.NewMessage.Event):
        """
        Handle incoming and outgoing messages.
        Check for commands (even if outgoing) and mentions (only if incoming).
        """
        if self._my_id is None:
            self._my_id = self.userbot.my_id
            self._my_username = self.userbot.my_username

        message = event.message
        text = message.text or ""

        # DEBUG: log messages in the bot chat to see if we see them
        bot_token = getattr(self.notifier, "bot_token", "")
        bot_id = int(bot_token.split(":")[0]) if ":" in bot_token else None
        
        if event.is_private and event.chat_id == bot_id:
            logger.debug("Bot chat message detected (chat_id: %s, outgoing: %s): %s", 
                         event.chat_id, message.out, text[:50])

        # 1. Handle command /report or /boats or button text (always allowed, even if outgoing)
        is_report_command = text.strip().lower() in ["/report", "/boats", "отчет", "📊 отчет по лодкам"]
        
        if self.boat_storage and is_report_command:
            # Check if this is a chat with the bot or the notification chat
            if event.chat_id == bot_id or event.chat_id == self.notifier.chat_id:
                logger.info("Command /report detected (outgoing=%s)", message.out)
                await self._send_boat_report()
                return

        # Filter out ignored chats
        if event.chat_id in getattr(config, "IGNORED_CHATS", []):
            return

        # 2. Skip other self-messages (mentions, etc.)
        if message.out or message.sender_id == self._my_id:
            return

        # Filter out messages from bots if IGNORE_BOTS is enabled
        if getattr(config, "IGNORE_BOTS", True):
            try:
                sender = await event.get_sender()
                if sender and getattr(sender, "bot", False):
                    return
            except Exception as e:
                logger.warning("Error fetching sender to check for bot: %s", e)

        if not text:
            return

        result = await self._check_mention(event)

        if result:
            mention_type, tag = result
            await self._send_alert(event, mention_type, tag)

    async def _send_boat_report(self):
        """Generate and send today's boat report grouped by pier and beautifully formatted."""
        import datetime
        from collections import defaultdict
        
        if not self.boat_storage:
            return

        events = self.boat_storage.get_todays_events()
        
        if not events:
            await self.notifier.send_notification("📊 <b>Сегодня событий по лодкам пока нет.</b>")
            return

        # 1. Group events by boat
        boat_events = defaultdict(list)
        for e in events:
            boat_events[e['boat_name']].append(e)

        # 2. Group boats by their LATEST pier
        pier_groups = defaultdict(list)
        for boat_name, items in boat_events.items():
            latest = items[-1]
            pier = latest.get('pier') or "Разное / Не указано"
            pier_groups[pier].append(boat_name)

        report_lines = ["📊 <b>Статус лодок (Пхукет):</b>\n"]
        
        for pier in sorted(pier_groups.keys()):
            report_lines.append(f"📍 <b>Пирс: {pier}</b>")
            
            for boat_name in sorted(pier_groups[pier]):
                items = boat_events[boat_name]
                latest = items[-1]
                
                # Format timeline
                timeline_parts = []
                last_status = None
                last_time = None
                
                for item in items:
                    try:
                        dt = datetime.datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00'))
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=datetime.timezone.utc)
                        local_dt = dt + datetime.timedelta(hours=7)
                        time_str = local_dt.strftime("%H:%M")
                    except Exception:
                        time_str = item['timestamp'].split(' ')[1][:5] if ' ' in item['timestamp'] else "??:??"
                    
                    status = item['status'].capitalize()
                    if status != last_status or time_str != last_time:
                        timeline_parts.append(f"<code>{time_str}</code> {status}")
                        last_status = status
                        last_time = time_str
                
                timeline = " ➔ ".join(timeline_parts)
                
                # Boat block with standard labeling
                report_lines.append(f"   🛥 <b>Лодка: {boat_name}</b>")
                
                if latest.get('program'):
                    report_lines.append(f"   📝 <b>Программа:</b> <i>{latest['program']}</i>")
                
                report_lines.append(f"   📈 <b>Статус:</b> {timeline}")
            
            report_lines.append("") # Spacer between piers

        final_text = "\n".join(report_lines).strip()
        await self.notifier.send_notification(
            final_text, 
            reply_markup=self.notifier.get_main_menu()
        )
        logger.info("Sent standardized boat report")

    async def _check_mention(self, event: events.NewMessage.Event) -> tuple[str, str] | None:
        """
        Run all registered rules to check for a mention.
        """
        for rule in self.rules:
            result = await rule.check(event, self._my_id, self._my_username)
            if result:
                return result
        return None

    async def _send_alert(self, event: events.NewMessage.Event, mention_type: str, tag: str):
        """
        Send notification about the mention.
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


def create_mention_handler(
    userbot: "UserbotClient", 
    notifier: "BaseNotifier",
    boat_storage: Optional["BoatStorage"] = None
) -> MentionHandler:
    """
    Factory function to create and register mention handler.
    """
    handler = MentionHandler(userbot, notifier, boat_storage)
    handler.register()
    return handler
