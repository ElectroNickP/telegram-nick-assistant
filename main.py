#!/usr/bin/env python3
"""
Telegram Nick Assistant - Main entry point.

Monitors mentions and replies, sends notifications to a chat with a button to open the message.
"""

import asyncio
import logging

# Configure logging before importing config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Import config (validates env and may exit)
from config import config

# Set log level from config
log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
logging.getLogger().setLevel(log_level)

logging.getLogger("telethon").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)

logger = logging.getLogger("main")


async def run():
    """Main entry point."""
    from userbot.client import create_client
    from notifier.bot import NotificationBot
    from userbot.handlers.mentions import create_mention_handler

    userbot = create_client(
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        session_name=config.SESSION_NAME,
    )

    notifier = NotificationBot(
        bot_token=config.BOT_TOKEN,
        chat_id=config.NOTIFICATION_CHAT_ID,
    )

    try:
        await userbot.start()

        create_mention_handler(userbot, notifier)

        # Optional: send startup notification to verify notifier works
        await notifier.send_notification(
            "Telegram Nick Assistant запущен. Мониторинг упоминаний и ответов активен."
        )
        logger.info("Startup notification sent")

        await userbot.run_until_disconnected()

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt...")
    except Exception as e:
        logger.error("Fatal error: %s", e, exc_info=True)
        raise
    finally:
        logger.info("Shutting down...")
        await notifier.close()
        await userbot.disconnect()
        logger.info("Stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
