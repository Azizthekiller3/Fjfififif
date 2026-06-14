from config import LOG_CHANNEL
from utils import get_group, update_group
from client import User
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

logger = logging.getLogger(__name__)


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
        return await m.edit("ɪɴᴄᴏʀʀᴇᴄᴛ ꜰᴏʀᴍᴀᴛ 🚫\nᴜꜱᴇ `/connect` ᴄʜᴀɴɴᴇʟ ɪᴅ")

    try:
        chat  = await bot.get_chat(channel)
        group_chat = await bot.get_chat(message.chat.id)
        c_link = chat.invite_link
        g_link = group_chat.invite_link
        try:
            await User.join_chat(c_link)
        except Exception as e:
            if "already a participant" not in str(e).lower():
                raise e
    except Exception as e:
        text = (
            f"🚫  ᴇʀʀᴏʀ  -  `{str(e)}`\n"
            f"ᴍᴀᴋᴇ ꜱᴜʀᴇ ᴛʜᴀᴛ ɪ ᴀᴍ ᴀᴅᴍɪɴ ɪɴ ᴛʜᴀᴛ ᴄʜᴀɴɴᴇʟ ᴀɴᴅ ɢʀᴏᴜᴘ "
            f"ᴡɪᴛʜ ᴀʟʟ ᴘᴇʀᴍɪꜱꜱɪᴏɴꜱ ᴀɴᴅ "
            f"{(user_acc.username or user_acc.mention)} ɪꜱ ɴᴏᴛ ʙᴀɴɴᴇᴅ ᴛʜᴇʀᴇ."
        )
        return await m.edit(text)

    await update_group(message.chat.id, {"channels": channels})
    await m.edit(
        f"ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴄᴏɴɴᴇᴄᴛᴇᴅ ᴛᴏ\n[{chat.title}]({c_link})",
        disable_web_page_preview=True
    )
    text = (
        f"#NewConnection\n\n"
        f"User: {message.from_user.mention}\n"
        f"Group: [{group_chat.title}]({g_link})\n"
        f"Channel: [{chat.title}]({c_link})"
    )
    if LOG_CHANNEL:
        await bot.send_message(chat_id=LOG_CHANNEL, text=text)


@Client.on_message(filters.group & filters.command("disconnect"))
async def disconnect(bot, message):
    m = await message.reply("<b>ᴘʟᴇᴀꜱᴇ  ᴡᴀɪᴛ...</b>")
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
            return await m.edit("ʏᴏᴜ ᴅɪᴅ ɴᴏᴛ ᴀᴅᴅᴇᴅ ᴛʜɪꜱ ᴄʜᴀɴɴᴇʟ ʏᴇᴛ")
        channels.remove(channel)
    except Exception:
        return await m.edit("ɪɴᴄᴏʀʀᴇᴄᴛ ꜰᴏʀᴍᴀᴛ 🚫\nᴜꜱᴇ `/disconnect` ᴄʜᴀɴɴᴇʟ ɪᴅ")

    # Try to leave the chat, but don't block disconnect if channel is banned/inaccessible
    channel_title = str(channel)
    try:
        chat = await bot.get_chat(channel)
        channel_title = chat.title
        try:
            await User.leave_chat(channel)
        except Exception as e:
            logger.warning(f"Could not leave chat {channel}: {e}")
    except Exception as e:
        logger.warning(f"Could not fetch chat {channel} (may be banned/deleted): {e}")

    await update_group(message.chat.id, {"channels": channels})
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
                    f"Group: [{group_chat.title}]({g_link})\n"
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
    user_id   = group["user_id"]
    user_name = group["user_name"]
    channels  = group["channels"]
    f_sub     = group["f_sub"]

    if message.from_user.id != user_id:
        return await message.reply(f"Only {user_name} can use this command 😁")
    if not channels:
        return await message.reply(
            "ᴛʜɪꜱ ɢʀᴏᴜᴘ ɪꜱ ᴄᴜʀʀᴇɴᴛʟʏ ɴᴏᴛ ᴄᴏɴɴᴇᴄᴛᴇᴅ ᴛᴏ ᴀɴʏ ᴄʜᴀɴɴᴇʟꜱ..\n"
            "ᴄᴏɴɴᴇᴄᴛ ᴏɴᴇ ᴜꜱɪɴɢ /connect"
        )

    async def _resolve_chat(cid):
        for client in (bot, User):
            try:
                return await client.get_chat(cid)
            except Exception:
                continue
        return None

    text = "📋 <b>ᴄᴏɴɴᴇᴄᴛᴇᴅ ᴄʜᴀɴɴᴇʟꜱ:</b>\n\n"
    buttons = []

    for channel in channels:
        chat = await _resolve_chat(channel)
        if chat:
            link = chat.invite_link or f"https://t.me/c/{str(channel).replace('-100', '')}/1"
            label = chat.title
            text += f"• <a href='{link}'>{chat.title}</a>\n"
        else:
            label = f"⚠️ {channel} (banned/deleted)"
            text += f"• <code>{channel}</code> _(banned/deleted)_\n"

        buttons.append([
            InlineKeyboardButton(
                f"❌ Disconnect: {label[:30]}",
                callback_data=f"dc_{channel}"
            )
        ])

    if f_sub:
        chat = await _resolve_chat(f_sub)
        if chat:
            link = chat.invite_link or f"https://t.me/c/{str(f_sub).replace('-100', '')}/1"
            text += f"\n🔒 ꜰꜱᴜʙ: <a href='{link}'>{chat.title}</a>"
        else:
            text += f"\n🔒 ꜰꜱᴜʙ: <code>{f_sub}</code> _(banned/deleted)_"

    await message.reply(
        text=text,
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@Client.on_callback_query(filters.regex(r"^dc_-?\d+$"))
async def disconnect_btn_cb(bot, update):
    """One-click disconnect from the /connections list — works even for banned channels."""
    try:
        # Only the group owner can use this button
        group = await get_group(update.message.chat.id)
        if not group:
            return await update.answer("Group not found.", show_alert=True)

        if update.from_user.id != group["user_id"]:
            return await update.answer("Only the group owner can disconnect channels.", show_alert=True)

        channel = int(update.data.split("_", 1)[1])
        channels = group.get("channels", []).copy()

        if channel not in channels:
            return await update.answer("This channel is already disconnected.", show_alert=True)

        channels.remove(channel)
        await update_group(update.message.chat.id, {"channels": channels})

        # Try to leave the chat (may fail if channel is banned — that's fine)
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

        await update.answer(f"✅ Disconnected from {channel_title}", show_alert=True)

        # Refresh the connections list in the same message
        if not channels:
            await update.message.edit(
                "✅ All channels disconnected.\nUse /connect to add a new one.",
                reply_markup=None
            )
        else:
            # Rebuild the updated list
            async def _resolve_chat(cid):
                for client in (bot, User):
                    try:
                        return await client.get_chat(cid)
                    except Exception:
                        continue
                return None

            new_text = "📋 <b>ᴄᴏɴɴᴇᴄᴛᴇᴅ ᴄʜᴀɴɴᴇʟꜱ:</b>\n\n"
            new_buttons = []
            for ch in channels:
                ch_chat = await _resolve_chat(ch)
                if ch_chat:
                    link = ch_chat.invite_link or f"https://t.me/c/{str(ch).replace('-100', '')}/1"
                    lbl = ch_chat.title
                    new_text += f"• <a href='{link}'>{ch_chat.title}</a>\n"
                else:
                    lbl = f"⚠️ {ch} (banned/deleted)"
                    new_text += f"• <code>{ch}</code> _(banned/deleted)_\n"
                new_buttons.append([
                    InlineKeyboardButton(
                        f"❌ Disconnect: {lbl[:30]}",
                        callback_data=f"dc_{ch}"
                    )
                ])

            f_sub = group.get("f_sub")
            if f_sub:
                ch_chat = await _resolve_chat(f_sub)
                if ch_chat:
                    link = ch_chat.invite_link or f"https://t.me/c/{str(f_sub).replace('-100', '')}/1"
                    new_text += f"\n🔒 ꜰꜱᴜʙ: <a href='{link}'>{ch_chat.title}</a>"
                else:
                    new_text += f"\n🔒 ꜰꜱᴜʙ: <code>{f_sub}</code> _(banned/deleted)_"

            await update.message.edit(
                text=new_text,
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup(new_buttons)
            )

        if LOG_CHANNEL:
            try:
                group_chat = await bot.get_chat(update.message.chat.id)
                await bot.send_message(
                    chat_id=LOG_CHANNEL,
                    text=(
                        f"#DisConnection\n\n"
                        f"User: {update.from_user.mention}\n"
                        f"Group: {group_chat.title}\n"
                        f"Channel: <code>{channel_title}</code>"
                    ),
                )
            except Exception:
                pass

    except Exception as e:
        logger.error(f"disconnect_btn_cb error: {e}", exc_info=True)
        await update.answer("Something went wrong. Please try again.", show_alert=True)
