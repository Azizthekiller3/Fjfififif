from config import LOG_CHANNEL
from utils import get_group, update_group
from pyrogram import Client, filters


def _get_user():
    """
    Lazily import and return the User client.
    Returns (User, error_text) — if the session is not connected,
    User is None and error_text explains why.
    """
    try:
        from client import User
        if not User.is_connected:
            return None, "⚠️ User session is not connected. Try again in a moment or contact the owner."
        return User, None
    except Exception as e:
        return None, f"⚠️ User session unavailable: {e}"


@Client.on_message(filters.group & filters.command("connect"))
async def connect(bot, message):
    m = await message.reply("<b>ᴄᴏɴɴᴇᴄᴛɪɴɢ...</b>")

    User, err = _get_user()
    if err:
        return await m.edit(err)

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
            f"🚫  ᴇʀʀᴏʀ  -  `{str(e)}`\n"
            f"ᴍᴀᴋᴇ ꜱᴜʀᴇ ᴛʜᴀᴛ ɪ ᴀᴍ ᴀᴅᴍɪɴ ɪɴ ᴛʜᴀᴛ ᴄʜᴀɴɴᴇʟ ᴀɴᴅ ɢʀᴏᴜᴘ "
            f"ᴡɪᴛʜ ᴀʟʟ ᴘᴇʀᴍɪꜱꜱɪᴏɴꜱ ᴀɴᴅ "
            f"{(user_acc.username or user_acc.mention)} ɪꜱ ɴᴏᴛ ʙᴀɴɴᴇᴅ ᴛʜᴇʀᴇ."
        )
        return await m.edit(text)

    await update_group(message.chat.id, {"channels": channels})
    await m.edit(
        f"ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴄᴏɴɴᴇᴄᴛᴇᴅ ᴛᴏ\n[{chat.title}]({c_link})",
        disable_web_page_preview=True,
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

    User, err = _get_user()
    if err:
        return await m.edit(err)

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

    try:
        chat       = await bot.get_chat(channel)
        group_chat = await bot.get_chat(message.chat.id)
        c_link     = chat.invite_link
        g_link     = group_chat.invite_link
        await User.leave_chat(channel)
    except Exception as e:
        text = (
            f"🚫  ᴇʀʀᴏʀ  - `{str(e)}`\n"
            "ᴍᴀᴋᴇ ꜱᴜʀᴇ ᴛʜᴀᴛ ɪ ᴀᴍ ᴀᴅᴍɪɴ ɪɴ ᴛʜᴀᴛ ᴄʜᴀɴɴᴇʟ ᴀɴᴅ ɢʀᴏᴜᴘ ᴡɪᴛʜ ᴀʟʟ ᴘᴇʀᴍɪꜱꜱɪᴏɴꜱ"
        )
        return await m.edit(text)

    await update_group(message.chat.id, {"channels": channels})
    await m.edit(
        f"ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴅɪꜱᴄᴏɴɴᴇᴄᴛᴇᴅ ꜰʀᴏᴍ [{chat.title}]({c_link})",
        disable_web_page_preview=True,
    )
    text = (
        f"#DisConnection\n\n"
        f"User: {message.from_user.mention}\n"
        f"Group: [{group_chat.title}]({g_link})\n"
        f"Channel: [{chat.title}]({c_link})"
    )
    if LOG_CHANNEL:
        await bot.send_message(chat_id=LOG_CHANNEL, text=text)


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

    # Lazy-import User for resolving channel titles — fall back to bot-only if unavailable
    User, _ = _get_user()

    async def _resolve_chat(cid):
        clients = [bot] + ([User] if User else [])
        for client in clients:
            try:
                return await client.get_chat(cid)
            except Exception:
                continue
        return None

    text = "ᴛʜɪꜱ ɢʀᴏᴜᴘ ɪꜱ ᴄᴏɴɴᴇᴄᴛᴇᴅ ᴡɪᴛʜ - \n\n"

    for channel in channels:
        chat = await _resolve_chat(channel)
        if chat:
            link = chat.invite_link or f"https://t.me/c/{str(channel).replace('-100', '')}/1"
            text += f"• [{chat.title}]({link})\n"
        else:
            text += f"• `{channel}` _(inaccessible)_\n"

    if f_sub:
        chat = await _resolve_chat(f_sub)
        if chat:
            link = chat.invite_link or f"https://t.me/c/{str(f_sub).replace('-100', '')}/1"
            text += f"\nꜰꜱᴜʙ: [{chat.title}]({link})"
        else:
            text += f"\nꜰꜱᴜʙ: `{f_sub}` _(inaccessible)_"

    await message.reply(text=text, disable_web_page_preview=True)
