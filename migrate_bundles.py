# migrate_bundles.py
import asyncio
from pyrogram import Client
from utils.db_utils.bundle_db import BundleDatabase
import config

db = BundleDatabase()
app = Client("migrate_bot", api_id=config.API_ID, api_hash=config.API_HASH, bot_token=config.BOT_TOKEN)

async def migrate():
    async with app:
        print("Starting Bundle Migration...")
        # Find bundles missing the hash
        bundles = list(db.collection.find({"file_hash": {"$exists": False}}))
        print(f"Found {len(bundles)} bundles to update.")
        
        for bundle in bundles:
            try:
                chat_id = int(bundle['chat_id'])
                msg_id = int(bundle['msg_id'])
                
                msg = await app.get_messages(chat_id, msg_id)
                if msg and (msg.video or msg.document):
                    media = msg.video or msg.document
                    file_unique_id = media.file_unique_id
                    file_hash = file_unique_id[:6] # Generate Hash
                    
                    db.collection.update_one(
                        {"_id": bundle["_id"]},
                        {"$set": {"file_hash": file_hash, "file_unique_id": file_unique_id}}
                    )
                    print(f"Updated: {bundle.get('title')[:20]} -> {file_hash}")
                await asyncio.sleep(0.2)
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())