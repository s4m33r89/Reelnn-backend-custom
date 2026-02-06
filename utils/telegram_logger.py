
from typing import Optional
from pyrogram import Client
from config import LOGS_CHAT
from logging import getLogger

LOGGER = getLogger(__name__)

async def send_log(client: Client, message: str, level: str = "INFO"):
    """
    Send a log message to the configured LOGS_CHAT.
    
    Args:
        client: The Pyrogram client instance
        message: The message to send
        level: Log level (INFO, WARNING, ERROR, etc.)
    """
    try:
        if not client or not client.is_connected:
            LOGGER.warning("Cannot send Telegram log: Client not connected")
            return
            
        formatted_message = f"**[{level}]** {message}"
        
        await client.send_message(LOGS_CHAT, formatted_message)
    except Exception as e:
        LOGGER.error(f"Failed to send log to Telegram: {str(e)}")


async def send_info(client, message):
    await send_log(client, message, "INFO")

async def send_warning(client, message):
    await send_log(client, message, "WARNING")

async def send_error(client, message, exception: Optional[Exception] = None):
    error_message = message
    if exception:
        error_message += f"\n\n**Exception:** `{str(exception)}`"
    await send_log(client, error_message, "ERROR")