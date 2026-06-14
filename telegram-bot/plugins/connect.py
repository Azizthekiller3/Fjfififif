import html
import logging
from config import LOG_CHANNEL
from utils import get_group, update_group
from client import User
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)


async def _resolve_chat(bot, cid):
    """Try to fetch a chat via bot first, then user session. Returns None if inaccessible."""
    for client in (bot, User):
        try:
            return await client.get_chat(cid)
        except Exception:
            continue
    return None


def _channel_label(channel_id: int, title: str | None) -> str:
    """Human-readable label for a channel — falls back to raw ID if title is unavailable."""
    if title:
        return title
    return f"⚠️ {channel_id} (banned/deleted)"


async def _build_connections_message(bot, channels: list, f_sub):
    """Build the HTML text and button rows for the /connections list."""
    text = "📋 <b>ᴄᴏɴɴᴇᴄᴛᴇᴅ ᴄʜᴀɴɴᴇʟꜱ:</b>\n\n"
    buttons = []

    for channel in channels:
        chat = await _resolve_chat(bot, channel)
        if chat:
            link = chat.invite_link or f"https://t.me/c/{str(channel).replace('-100', '')}/1"
            title_safe = html.escape(chat.title or str(channel))
            text += f"• <a href='{link}'>{title_safe}</a>\n"
            label = chat.title or str(channel)
        else:
            text += f"• <code>{channel}</code> <i>(banned/deleted)</i>\n"
            label = f"⚠️ {channel} (banned/deleted)"

        buttons.append([
            InlineKeyboardButton(
                f"❌ Disconnect: {label[:30]}",
                callback_data=f"dc_{channel}"
            )
        ])

    if f_sub:
        chat = await _resolve_chat(bot, f_sub)
        if chat:
            link = chat.invite_link or f"https://t.me/c/{str(f_sub).replace('-100', '')}/1"
            title_safe = html.escape(chat.title or str(f_sub))
            text += f"\n🔒 ꜰꜱᴜʙ: <a href='{link}'>{title_safe}</a>"
        else:
            text += f"\n🔒 ꜰꜱᴜʙ: <code>{f_sub}</code> <i>(banned/deleted)</i>"

    return text, buttons


@Client.on_message(filters.group & filters.command("connect"))
async def connect(bot, message):
    m = await message.reply("<b>ᴄᴏɴɴᴇᴄᴛɪɴɢ...</b>")
    user_acc = await User.get_me()
    try:
        group     = await get_group(message.chat.id)
        user_id   = group["user_id"]
        user_name = group["user_name"]
        verified  = group["verified"]
        channels  = group["channels"].copy()
    except Exception:
        return await bot.leave_chat(message.chat.id)

    if message.from_user.id != user_id:
        return await m.edit(f"Only {user_name} can use this command 😁")
    if not verified:
        return await m.edit("ᴛʜɪꜱ ᴄʜᴀᴛ ɪꜱ ɴᴏᴛ ᴠᴇʀɪꜰɪᴇᴅ 🚫\nᴜꜱᴇ /verify")

    try:
        channel = int(message.command[-1])
        if channel in channels:
            return await message.reply("ᴛʜɪꜱ ᴄʜᴀɴɴᴇʟ ɪꜱ ᴀʟʀᴇᴀᴅʏ ᴄᴏɴɴᴇᴄᴛᴇᴅ")
        channels.append(channel)
    except Exception:
        return await m.edit("ɪɴᴄᴏʀʀᴇᴄᴛ ꜰᴏʀᴍᴀᴛ 🚫\nᴜꜱᴇ <code>/connect CHANNEL_ID</code>")

    try:
        chat       = await bot.get_chat(channel)
        group_chat = await bot.get_chat(message.chat.id)
        c_link     = chat.invite_link
        g_link     = group_chat.invite_link
        try:
            await User.join_chat(c_link)
        except Exception as e:
            if "already a participant" not in str(e).lower():
                raise e
    except Exception as e:
        text = (
            f"🚫 <b>Error:</b> <code>{html.escape(str(e))}</code>\n"
            f"Make sure I am admin in that channel and group with all permissions, "
            f"and {html.escape(user_acc.username or str(user_acc.id))} is not banned there."
        )
        return await m.edit(text)

    await update_group(message.chat.id, {"channels": channels})
    await m.edit(
        f"ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴄᴏɴɴᴇᴄᴛᴇᴅ ᴛᴏ <a href='{c_link}'>{html.escape(chat.title)}</a>",
        disable_web_page_preview=True
    )
    if LOG_CHANNEL:
        try:
            await bot.send_message(
                chat_id=LOG_CHANNEL,
                text=(
                    f"#NewConnection\n\n"
                    f"User: {message.from_user.mention}\n"
                    f"Group: <a href='{g_link}'>{html.escape(group_chat.title)}</a>\n"
                    f"Channel: <a href='{c_link}'>{html.escape(chat.title)}</a>"
                ),
            )
        except Exception:
            pass


@Client.on_message(filters.group & filters.command("disconnect"))
async def disconnect(bot, message):
    m = await message.reply("<b>ᴘʟᴇᴀꜱᴇ ᴡᴀɪᴛ...</b>")
    try:
        group     = await get_group(message.chat.id)
        user_id   = group["user_id"]
        user_name = group["user_name"]
        verified  = group["verified"]
        channels  = group["channels"].copy()
    except Exception:
        return await bot.leave_chat(message.chat.id)

    if message.from_user.id != user_id:
        return await m.edit(f"Only {user_name} can use this command 😁")
    if not verified:
        return await m.edit("ᴛʜɪꜱ ᴄʜᴀᴛ ɪꜱ ɴᴏᴛ ᴠᴇʀɪꜰɪᴇᴅ 🚫\nᴜꜱᴇ /verify")

    try:
        channel = int(message.command[-1])
        if channel not in channels:
            return await m.edit("ʏᴏᴜ ᴅɪᴅ ɴᴏᴛ ᴀᴅᴅ ᴛʜɪꜱ ᴄʜᴀɴɴᴇʟ ʏᴇᴛ")
        channels.remove(channel)
    except Exception:
        return await m.edit("ɪɴᴄᴏʀʀᴇᴄᴛ ꜰᴏʀᴍᴀᴛ 🚫\nᴜꜱᴇ <code>/disconnect CHANNEL_ID</code>")

    # Always remove from DB first — don't let a banned/inaccessible channel block the action
    await update_group(message.chat.id, {"channels": channels})

    # Best-effort: resolve title and leave the chat
    channel_title = str(channel)
    try:
        chat = await bot.get_chat(channel)
        channel_title = html.escape(chat.title)
        try:
            await User.leave_chat(channel)
        except Exception as e:
            logger.warning(f"Could not leave chat {channel}: {e}")
    except Exception as e:
        logger.warning(f"Could not fetch chat {channel} (likely banned/deleted): {e}")

    await m.edit(f"ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴅɪꜱᴄᴏɴɴᴇᴄᴛᴇᴅ ꜰʀᴏᴍ <code>{channel_title}</code>")

    if LOG_CHANNEL:
        try:
            group_chat = await bot.get_chat(message.chat.id)
            g_link = group_chat.invite_link
            await bot.send_message(
                chat_id=LOG_CHANNEL,
                text=(
                    f"#DisConnection\n\n"
                    f"User: {message.from_user.mention}\n"
                    f"Group: <a href='{g_link}'>{html.escape(group_chat.title)}</a>\n"
                    f"Channel: <code>{channel_title}</code>"
                ),
            )
        except Exception:
            pass


@Client.on_message(filters.group & filters.command("connections"))
async def connections(bot, message):
    group = await get_group(message.chat.id)
    if not group:
        return await message.reply("ᴛʜɪꜱ ɢʀᴏᴜᴘ ɪꜱ ɴᴏᴛ ʀᴇɢɪꜱᴛᴇʀᴇᴅ ʏᴇᴛ.\nᴜꜱᴇ /verify")

    user_id  = group["user_id"]
    user_name = group["user_name"]
    channels = group["channels"]
    f_sub    = group["f_sub"]

    if message.from_user.id != user_id:
        return await message.reply(f"Only {user_name} can use this command 😁")
    if not channels:
        return await message.reply(
            "ᴛʜɪꜱ ɢʀᴏᴜᴘ ɪꜱ ᴄᴜʀʀᴇɴᴛʟʏ ɴᴏᴛ ᴄᴏɴɴᴇᴄᴛᴇᴅ ᴛᴏ ᴀɴʏ ᴄʜᴀɴɴᴇʟꜱ.\n"
            "ᴄᴏɴɴᴇᴄᴛ ᴏɴᴇ ᴜꜱɪɴɢ /connect"
        )

    text, buttons = await _build_connections_message(bot, channels, f_sub)
    await message.reply(
        text=text,
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@Client.on_callback_query(filters.regex(r"^dc_-?\d+$"))
async def disconnect_btn_cb(bot, update):
    """One-click disconnect — works even for banned/deleted channels."""
    try:
        group = await get_group(update.message.chat.id)
        if not group:
            return await update.answer("Group not found.", show_alert=True)

        if update.from_user.id != group["user_id"]:
            return await update.answer("Only the group owner can disconnect channels.", show_alert=True)

        channel  = int(update.data.split("_", 1)[1])
        channels = group.get("channels", []).copy()

        if channel not in channels:
            return await update.answer("This channel is already disconnected.", show_alert=True)

        channels.remove(channel)

        # Always persist first — don't let a banned channel block the action
        await update_group(update.message.chat.id, {"channels": channels})

        # Best-effort: resolve title and leave
        channel_title = str(channel)
        try:
            chat = await bot.get_chat(channel)
            channel_title = chat.title
            try:
                await User.leave_chat(channel)
            except Exception as e:
                logger.warning(f"Could not leave chat {channel}: {e}")
        except Exception as e:
            logger.warning(f"Could not fetch chat {channel} (likely banned/deleted): {e}")

        # Notify the user — must answer BEFORE editing to avoid timeout
        await update.answer(f"✅ Disconnected from {channel_title}", show_alert=True)

        # Refresh the message — wrap separately so a failure here never double-answers
        try:
            if not channels:
                await update.message.edit(
                    "✅ All channels disconnected.\nUse /connect to add a new one.",
                    reply_markup=None
                )
            else:
                f_sub = group.get("f_sub")
                new_text, new_buttons = await _build_connections_message(bot, channels, f_sub)
                await update.message.edit(
                    text=new_text,
                    disable_web_page_preview=True,
                    reply_markup=InlineKeyboardMarkup(new_buttons)
                )
        except Exception as e:
            logger.warning(f"Could not refresh connections message: {e}")

        if LOG_CHANNEL:
            try:
                group_chat = await bot.get_chat(update.message.chat.id)
                await bot.send_message(
                    chat_id=LOG_CHANNEL,
                    text=(
                        f"#DisConnection\n\n"
                        f"User: {update.from_user.mention}\n"
                        f"Group: {html.escape(group_chat.title)}\n"
                        f"Channel: <code>{html.escape(channel_title)}</code>"
                    ),
                )
            except Exception:
                pass

    except Exception as e:
        logger.error(f"disconnect_btn_cb error: {e}", exc_info=True)
        try:
            await update.answer("Something went wrong. Please try again.", show_alert=True)
        except Exception:
            pass
