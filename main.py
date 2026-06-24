#!/usr/bin/env python3
"""
Telegram Nick Assistant - Main entry point.

Monitors mentions, replies, and boat statuses.
Sends notifications and reports to a chat.
"""

import asyncio
import logging
import datetime

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


async def daily_report_task(storage, notifier):
    """Background task to send daily boat status report at 19:00."""
    logger.info("Daily report task started")
    while True:
        now = datetime.datetime.now()
        # Schedule for 19:00
        target_time = now.replace(hour=19, minute=0, second=0, microsecond=0)
        
        if now >= target_time:
            target_time += datetime.timedelta(days=1)
            
        wait_seconds = (target_time - now).total_seconds()
        logger.info("Next daily report scheduled for %s (waiting %.1f hours)", 
                    target_time.strftime("%Y-%m-%d %H:%M:%S"), wait_seconds / 3600)
        
        try:
            await asyncio.sleep(wait_seconds)
            
            # Generate report
            latest_statuses = storage.get_latest_status_all_boats()
            if latest_statuses:
                report_lines = ["📅 <b>Ежедневный отчет по лодкам:</b>\n"]
                for item in latest_statuses:
                    time_str = item['timestamp'].split(' ')[1][:5] if ' ' in item['timestamp'] else ""
                    status_icon = "🚢" if "departed" in item['status'].lower() else "✅"
                    line = f"{status_icon} <b>{item['boat_name']}</b>: {item['status']} ({time_str})"
                    if item.get('pier'):
                        line += f" | {item['pier']}"
                    report_lines.append(line)
                
                await notifier.send_notification("\n".join(report_lines))
                logger.info("Daily report sent")
            else:
                logger.info("Daily report skipped (no data today)")
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Error in daily report task: %s", e, exc_info=True)
            await asyncio.sleep(60)


async def daily_diary_reminder_task(storage, notifier):
    """Background task to remind the captain to record a video diary at 21:00."""
    logger.info("Daily diary reminder task started")
    while True:
        now = datetime.datetime.now()
        # Schedule for 21:00 local time (script runs on local time timezone if system timezone is set, or we assume server is local)
        # Assuming the server is on Phuket time (user mentioned local time constraint)
        target_time = now.replace(hour=21, minute=0, second=0, microsecond=0)
        
        if now >= target_time:
            target_time += datetime.timedelta(days=1)
            
        wait_seconds = (target_time - now).total_seconds()
        logger.info("Next diary reminder scheduled for %s (waiting %.1f hours)", 
                    target_time.strftime("%Y-%m-%d %H:%M:%S"), wait_seconds / 3600)
        
        try:
            await asyncio.sleep(wait_seconds)
            
            # Check if there's already an entry for today
            if not storage.has_diary_entry_for_today():
                reminder_text = (
                    "🔔 <b>Капитан, вы не записали видео-дневник за сегодня!</b>\n\n"
                    "Зафиксируйте сегодняшний день: запишите мне кружочек прямо сейчас."
                )
                await notifier.send_notification(reminder_text, reply_markup=notifier.get_main_menu())
                logger.info("Diary reminder sent")
            else:
                logger.info("Diary reminder skipped (already recorded today)")
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Error in daily diary reminder task: %s", e, exc_info=True)
            await asyncio.sleep(60)


async def run():
    """Main entry point."""
    from userbot.client import create_client
    from notifier.bot import NotificationBot
    from userbot.handlers.mentions import create_mention_handler
    from userbot.handlers.boats import BoatHandler
    from userbot.handlers.diary import DiaryHandler
    from userbot.storage import BoatStorage

    # Initialize components
    storage = BoatStorage()
    
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

        # Mention and Command handler
        create_mention_handler(userbot, notifier, storage)
        
        # Boat status tracker
        boat_handler = BoatHandler(userbot, storage)
        boat_handler.register()

        # Startup history scan to backfill today's data
        await boat_handler.scan_history()

        # Diary handler
        diary_handler = DiaryHandler(userbot, notifier, storage)
        diary_handler.register()

        # Start background tasks
        report_task = asyncio.create_task(daily_report_task(storage, notifier))
        diary_task = asyncio.create_task(daily_diary_reminder_task(storage, notifier))

        # Optional: send startup notification to verify notifier works
        await notifier.send_notification(
            "Telegram Nick Assistant запущен.\n"
            "Мониторинг упоминаний и лодок активен.",
            reply_markup=notifier.get_main_menu()
        )
        logger.info("Startup notification sent")

        await userbot.run_until_disconnected()
        
        # Shutdown tasks
        report_task.cancel()
        diary_task.cancel()
        await asyncio.gather(report_task, diary_task, return_exceptions=True)

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt...")
    except Exception as e:
        err_type = type(e).__name__
        if err_type == "TypeNotFoundError":
            logger.error(
                "Fatal: TypeNotFoundError — сессия, скорее всего, общая с другим приложением (например Best My Assistant). "
                "Решение: в .env задайте SESSION_NAME=nick_assistant_session, удалите старый .session файл из каталога проекта, "
                "запустите один раз вручную (python main.py), войдите по телефону/коду, затем запускайте сервис. Подробно: README, раздел «Типичные ошибки по логам»."
            )
        else:
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
