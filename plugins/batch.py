from pyrogram import Client, filters
from pyrogram.types import Message
import re
import asyncio
import random
import config

from app import LOGGER
from utils.telegram_logger import send_info, send_error, send_warning
from plugins.video_message import message_queue, start_workers

TELEGRAM_LINK_PATTERN = r"https://t\.me/(?:c/)?([^/]+)/(\d+)"

@Client.on_message(filters.command("batch") & filters.user(config.SUDO_USERS))
async def batch_process(client: Client, message: Message):
    """
    Process multiple old Telegram messages and queue media for processing.

    Usage:
    /batch https://t.me/c/123456789/100 https://t.me/c/123456789/200
    """
    try:
        # -----------------------------
        # 1. Validate input
        # -----------------------------
        if len(message.command) < 3:
            await message.reply_text(
                "⚠️ Please provide both start and end message links.\n\n"
                "Example:\n"
                "/batch https://t.me/c/123456789/100 https://t.me/c/123456789/200"
            )
            return

        start_link = message.command[1]
        end_link = message.command[2]

        start_match = re.match(TELEGRAM_LINK_PATTERN, start_link)
        end_match = re.match(TELEGRAM_LINK_PATTERN, end_link)

        if not start_match or not end_match:
            await message.reply_text("⚠️ Invalid Telegram message link format.")
            return

        start_chat, start_id = start_match.groups()
        end_chat, end_id = end_match.groups()

        if start_chat != end_chat:
            await message.reply_text("⚠️ Both links must be from the same chat.")
            return

        chat_id = int(f"-100{start_chat}") if start_chat.isdigit() else start_chat
        start_id = int(start_id)
        end_id = int(end_id)

        if end_id < start_id:
            start_id, end_id = end_id, start_id

        total_messages = end_id - start_id + 1

        # -----------------------------
        # 2. Start workers (NO cache updates during batch)
        # -----------------------------
        await start_workers(update_cache=False)

        status_message = await message.reply_text(
            f"🔄 Starting batch processing\n\n"
            f"Chat: {chat_id}\n"
            f"Range: {start_id} → {end_id}\n"
            f"Total messages: {total_messages}"
        )

        await send_info(
            client,
            f"Batch started: {total_messages} messages from chat {chat_id}"
        )

        # -----------------------------
        # 3. Iterate messages & enqueue media
        # -----------------------------
        queued = 0

        for current_msg_id in range(start_id, end_id + 1):
            try:
                msg = await client.get_messages(chat_id, current_msg_id)

                if msg and (msg.video or msg.document or msg.animation):
                    await message_queue.put((client, msg))
                    queued += 1

                # Telegram-safe delay (NOT too slow)
                await asyncio.sleep(random.uniform(1.2, 2.5))

                # Progress update every 25 messages
                if current_msg_id % 25 == 0:
                    await status_message.edit_text(
                        f"🔄 Batch in progress\n\n"
                        f"Checked: {current_msg_id - start_id + 1}/{total_messages}\n"
                        f"Queued media: {queued}\n"
                        f"Current queue size: {message_queue.qsize()}"
                    )

            except Exception as e:
                err = str(e).lower()

                if "message_not_found" in err or "message not found" in err:
                    continue

                if "flood_wait" in err:
                    LOGGER.warning("FloodWait detected during batch, sleeping 5s")
                    await asyncio.sleep(5)
                    continue

                LOGGER.error(f"Batch error at message {current_msg_id}: {e}")
                await send_warning(
                    client,
                    f"Batch error at message {current_msg_id}: {e}"
                )

        # -----------------------------
        # 4. Final status
        # -----------------------------
        await status_message.edit_text(
            f"✅ Batch completed successfully\n\n"
            f"Messages checked: {total_messages}\n"
            f"Media queued: {queued}\n"
            f"Final queue size: {message_queue.qsize()}\n\n"
            f"🔄 Workers are processing the queue."
        )

        await send_info(
            client,
            f"Batch completed: {queued} media items queued from {total_messages} messages"
        )

    except Exception as e:
        LOGGER.exception(e)
        await send_error(client, "Batch processing failed", e)
        await message.reply_text(f"❌ Batch failed: {e}")