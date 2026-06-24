#!/usr/bin/env python3
"""
Self-check: verify mention detection logic using the new modular rules.
Run: python test_mention_logic.py
"""
import asyncio
from unittest.mock import MagicMock
from userbot.handlers.rules import UsernameMentionRule, IDMentionRule
from telethon.tl.types import MessageEntityMention, MessageEntityMentionName


async def test_username_rule():
    """UsernameMentionRule correctly extracts @username."""
    rule = UsernameMentionRule()
    my_username = "Pankonick"
    
    # Mock event
    event = MagicMock()
    event.message.text = "@Pankonick привет"
    event.message.message = "@Pankonick привет"
    event.message.entities = [MessageEntityMention(offset=0, length=10)]
    
    result = await rule.check(event, 123456, my_username)
    assert result == ("упомянул вас", "mention"), f"Got {result!r}"
    print("OK: UsernameMentionRule extracts @Pankonick")

    # ASCII in middle
    event.message.text = "Hi @Pankonick!"
    event.message.message = "Hi @Pankonick!"
    event.message.entities = [MessageEntityMention(offset=3, length=10)]
    result2 = await rule.check(event, 123456, my_username)
    assert result2 == ("упомянул вас", "mention"), f"Got {result2!r}"
    print("OK: UsernameMentionRule middle of text")

    # Emoji in text causing surrogate pair offset shift
    # 😊 takes 1 char in Python, but 2 code units in UTF-16.
    # String: "😊 @Pankonick"
    # Entities: offset=3, length=10
    event.message.text = "😊 @Pankonick"
    event.message.message = "😊 @Pankonick"
    event.message.entities = [MessageEntityMention(offset=3, length=10)]
    result3 = await rule.check(event, 123456, my_username)
    assert result3 == ("упомянул вас", "mention"), f"Got {result3!r}"
    print("OK: UsernameMentionRule with surrogate pair emoji")


async def test_id_rule():
    """IDMentionRule matches by user_id."""
    rule = IDMentionRule()
    my_id = 577784602
    
    event = MagicMock()
    event.message.entities = [MessageEntityMentionName(offset=0, length=10, user_id=my_id)]
    
    result = await rule.check(event, my_id, "any")
    assert result == ("упомянул вас", "mention"), f"Got {result!r}"
    print("OK: IDMentionRule matches by user_id")


async def main():
    await test_username_rule()
    await test_id_rule()
    print("\nAll modular rule checks passed.")


if __name__ == "__main__":
    asyncio.run(main())
