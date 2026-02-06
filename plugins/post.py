from pyrogram import Client
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import config
from config import SUDO_USERS


@Client.on_message(
    filters.command("post_updates", prefixes="/")
    & filters.private
    & filters.user(SUDO_USERS)
)
async def post_updates_command(client: Client, message: Message):

    status = "Enabled" if config.POST_UPDATES else "Disabled"

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"Toggle Updates {'OFF' if config.POST_UPDATES else 'ON'}",
                    callback_data="toggle_post_updates",
                )
            ]
        ]
    )

    await message.reply_text(
        f"**Current Post Updates Status**: {status}\n\nUse the button below to toggle post updates mode.",
        reply_markup=keyboard,
    )


@Client.on_callback_query(filters.regex("^toggle_post_updates$"))
async def toggle_post_updates_callback(client, callback_query):
    try:
        config.POST_UPDATES = not config.POST_UPDATES

        new_status = "Enabled" if config.POST_UPDATES else "Disabled"

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"Toggle Updates {'OFF' if config.POST_UPDATES else 'ON'}",
                        callback_data="toggle_post_updates",
                    )
                ]
            ]
        )

        await callback_query.message.edit_text(
            f"**Post Updates Status**: {new_status}\n\nUse the button below to toggle post updates mode.",
            reply_markup=keyboard,
        )

        await callback_query.answer(
            f"Post updates mode {new_status}. Change is temporary and will reset on restart."
        )

    except Exception as e:

        await callback_query.answer(f"Error: {str(e)}", show_alert=True)
