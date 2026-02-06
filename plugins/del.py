from pyrogram import Client
from pyrogram import filters
from pyrogram.types import Message
import re
from utils.db_utils.movie_db import MovieDatabase
from utils.db_utils.show_db import ShowDatabase
from config import SUDO_USERS
from utils.telegram_logger import send_info, send_error, send_warning

@Client.on_message(filters.command("del", prefixes="/") & filters.private & filters.user(SUDO_USERS))
async def del_command(client: Client, message: Message):
    
    command_parts = message.text.split(maxsplit=1)
    
    if len(command_parts) < 2:
        await message.reply("Please provide a URL to delete. Format: /del https://domain.com/movie/1234567")
        return
    
    url = command_parts[1].strip()
    await send_info(client, f"🗑️ Delete request received for URL: {url}")
    
    pattern = r"https?://[^/]+/(movie|show)/(\d+)"
    match = re.match(pattern, url)
    
    if not match:
        await message.reply("Invalid URL format. Expected: URL ending with /movie/ID or /show/ID")
        await send_warning(client, f"❌ Invalid URL format for deletion: {url}")
        return
    
    content_type, content_id = match.groups()
    content_id = int(content_id)
    
    try:
        if content_type == "movie":
            db = MovieDatabase()
            result = db.delete_movie(content_id)
            
        else:  
            db = ShowDatabase()
            result = db.delete_show(content_id)
            
        
        if result["status"] == "success":
            await message.reply(f"Successfully deleted {content_type} with ID {content_id}.")
            await send_info(client, f"✅ Successfully deleted {content_type} with ID {content_id}")
        elif result["status"] == "not_found":
            await message.reply(f"{content_type.capitalize()} with ID {content_id} not found in database.")
            await send_warning(client, f"⚠️ {content_type.capitalize()} with ID {content_id} not found for deletion")
        else:
            await message.reply(f"Error deleting {content_type}: {result['message']}")
            await send_error(client, f"Error deleting {content_type} with ID {content_id}: {result['message']}")
    except Exception as e:
        await message.reply(f"Error during deletion: {str(e)}")
        await send_error(client, f"Exception during deletion of {content_type} with ID {content_id}", e)