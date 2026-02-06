from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import PeerIdInvalid, ChannelPrivate
from utils.db_utils.movie_db import MovieDatabase
from utils.db_utils.show_db import ShowDatabase
from utils.db_utils.bundle_db import BundleDatabase
import asyncio
import logging
import config

# Configure logging
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

scheduled_deletions = {}

async def delete_after_delay(client, chat_id, message_id, delay_seconds):
    """Delete a message after specified delay"""
    try:
        await asyncio.sleep(delay_seconds)
        await client.delete_messages(chat_id, message_id)
        LOGGER.info(f"Auto-deleted message {message_id} in chat {chat_id}")
        
        if (chat_id, message_id) in scheduled_deletions:
            del scheduled_deletions[(chat_id, message_id)]
    except Exception as e:
        LOGGER.error(f"Error deleting message {message_id} in chat {chat_id}: {str(e)}")

# --- Filters ---

LINK_FLITER = filters.private & filters.create(
    lambda _, __, msg: msg.text and msg.text.startswith("/start file_")
)

BUNDLE_FILTER = filters.private & filters.create(
    lambda _, __, msg: msg.text and msg.text.startswith("/start bundle_")
)

# --- Handlers ---

@Client.on_message(BUNDLE_FILTER)
async def forward_bundle(client: Client, message: Message):
    """
    Handle bundle download requests (Season Packs)
    Link format: https://t.me/bot?start=bundle_<file_hash>
    """
    try:
        LOGGER.info(f"Bot received bundle command: {message.text}")
        processing_msg = await message.reply_text("Processing your request, please wait...")
        
        try:
            # Extract Hash/ID
            command_args = message.text.split("bundle_")[1]
            identifier = command_args.split("&")[0].split()[0].strip()
            
            LOGGER.info(f"Extracted identifier: {identifier}")
        except IndexError:
             await processing_msg.edit_text("Invalid bundle link format.")
             return

        # Look up bundle in DB
        LOGGER.info("Querying BundleDatabase...")
        bundle_db = BundleDatabase()
        bundle = bundle_db.get_bundle_by_hash_or_id(identifier)
        
        if not bundle:
            LOGGER.warning(f"Bundle NOT found in DB for: {identifier}")
            await processing_msg.edit_text("Sorry, bundle not found in database.")
            return

        LOGGER.info(f"Bundle found: {bundle.get('title', 'Unknown Title')}")
        await processing_msg.edit_text("Found your bundle! Forwarding it now...")

        # Get details
        try:
            chat_id = int(bundle.get("chat_id"))
            msg_id = int(bundle.get("msg_id"))
            LOGGER.info(f"Targeting Chat: {chat_id}, Message: {msg_id}")
        except (ValueError, TypeError):
            LOGGER.error(f"Invalid chat_id/msg_id in DB: {bundle}")
            await processing_msg.edit_text("Error: Invalid bundle data.")
            return

        # Forward the file
        try:
            # First, try get_messages to verify access/existence
            # This helps wake up the peer for the bot if needed
            # await client.get_messages(chat_id, msg_id) 
            
            forwarded_msg = await client.forward_messages(
                chat_id=message.chat.id,
                from_chat_id=chat_id,
                message_ids=msg_id,
                drop_author=True
            )
            LOGGER.info("Message forwarded successfully")
        except PeerIdInvalid:
            LOGGER.error(f"PeerIdInvalid: Bot hasn't seen chat {chat_id}")
            await processing_msg.edit_text("Error: Bot cannot access the source channel. Make sure the bot is an admin there.")
            return
        except ChannelPrivate:
            LOGGER.error(f"ChannelPrivate: Bot kicked or not admin in {chat_id}")
            await processing_msg.edit_text("Error: Source channel is private and bot cannot access it.")
            return
        except Exception as e:
            LOGGER.error(f"Failed to forward message: {e}")
            await processing_msg.edit_text("Error: Could not forward the file. Please report this.")
            return

        # Schedule auto-delete
        task = asyncio.create_task(delete_after_delay(client, message.chat.id, forwarded_msg.id, 60*config.DELETE_AFTER_MINUTES))
        scheduled_deletions[(message.chat.id, forwarded_msg.id)] = task

        await message.reply_text("Please forward this file to your saved messages. This file will be deleted in 10 minutes.")
        await processing_msg.delete()

    except Exception as e:
        LOGGER.exception(f"Unhandled error in forward_bundle")
        if 'processing_msg' in locals():
            await processing_msg.edit_text("Sorry, a critical error occurred.")
        else:
            await message.reply_text("Sorry, a critical error occurred.")


@Client.on_message(LINK_FLITER, -2)
async def forward_(client: Client, message: Message):
    """
    Handle standard episode/movie download requests
    """
    try:
        processing_msg = await message.reply_text("Processing your request, please wait...")
        
        token = message.text.split("file_")[1]
        details = token.split("_")
        
        if len(details) < 5:
            await processing_msg.edit_text("Invalid file link format.")
            return
            
        id = details[0]
        media_type = details[1]
        quality = details[2]
        season = details[3]
        episode = details[4]

        if media_type == "m":  
            movie_db = MovieDatabase()
            try:
                movie = movie_db.find_movie_by_id(int(id))
                if not movie:
                    await processing_msg.edit_text("Sorry, movie not found.")
                    return
                    
                file_data = movie["quality"][int(quality)]
                        
                if not file_data or "msg_id" not in file_data or "chat_id" not in file_data:
                    await processing_msg.edit_text(f"Sorry, {quality} quality not available for this movie.")
                    return
                
                await processing_msg.edit_text("Found your file! Forwarding it now...")
                
                forwarded_msg = await client.forward_messages(
                    chat_id=message.chat.id,
                    from_chat_id=file_data["chat_id"],
                    message_ids=file_data["msg_id"],
                    drop_author=True
                )
                
                task = asyncio.create_task(delete_after_delay(client, message.chat.id, forwarded_msg.id, 60*config.DELETE_AFTER_MINUTES))
                scheduled_deletions[(message.chat.id, forwarded_msg.id)] = task

                await message.reply_text("Please forward this file to your saved messages. This file will be deleted in 10 minutes.")
                await processing_msg.delete()
                
            finally:
                pass
                
        elif media_type == "s":  
            show_db = ShowDatabase()
            try:
                show = show_db.find_show_by_id(int(id))
                if not show:
                    await processing_msg.edit_text("Sorry, show not found.")
                    return
                    
                season_data = None
                for s in show.get("season", []):
                    if s["season_number"] == int(season):
                        season_data = s
                        break
                        
                if not season_data:
                    await processing_msg.edit_text(f"Sorry, season {season} not found for this show.")
                    return
                    
                episode_data = None
                for e in season_data.get("episodes", []):
                    if e["episode_number"] == int(episode):
                        episode_data = e
                        break
                        
                if not episode_data:
                    await processing_msg.edit_text(f"Sorry, episode {episode} not found in season {season}.")
                    return
                    
                file_data = episode_data["quality"][int(quality)]
                        
                if not file_data or "msg_id" not in file_data or "chat_id" not in file_data:
                    await processing_msg.edit_text(f"Sorry, {quality} quality not available for this episode.")
                    return
                
                await processing_msg.edit_text("Found your file! Forwarding it now...")
                
                forwarded_msg = await client.forward_messages(
                    chat_id=message.chat.id,
                    from_chat_id=file_data["chat_id"],
                    message_ids=file_data["msg_id"],
                    drop_author=True
                )
                
                task = asyncio.create_task(delete_after_delay(client, message.chat.id, forwarded_msg.id, 60*config.DELETE_AFTER_MINUTES))
                scheduled_deletions[(message.chat.id, forwarded_msg.id)] = task

                await processing_msg.delete()
                
            finally:
                pass
                
        else:
            await processing_msg.edit_text("Invalid media type. Expected 'm' for movie or 's' for show.")
            
    except Exception as e:
        if 'processing_msg' in locals():
            await processing_msg.edit_text(f"Sorry, an error occurred while processing your request.")
        else:
            await message.reply_text(f"Sorry, an error occurred while processing your request.")