import asyncio
import time
import uuid
from config import OWNER_ID
from utils import get_users, get_groups
from database import delete_user, delete_group
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

_pending: dict = {}
_PENDING_TTL = 300


def _prune_pending():
    now = time.time()
    expired = [k for k, v in _pending.items() if now - v.get("ts", now) > _PENDING_TTL]
    for k in expired:
        _pending.pop(k, None)


async def _copy_to(br_msg, chat_id: int) -> bool:
    try:
        await br_msg.copy(chat_id)
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await _copy_to(br_msg, chat_id)
    except Exception:
        return False
    return True


async def _copy_to_group(br_msg, chat_id: int) -> bool:
    try:
        h = await br_msg.copy(chat_id)
        try:
            await h.pin()
        except Exception:
            pass
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await _copy_to_group(br_msg, chat_id)
    except Exception:
        return False
    return True


def _estimate(count: int) -> str:
    secs = max(1, count // 20)
    if secs < 60:
        return f"~{secs}s"
    return f"~{secs // 60}m {secs % 60}s"


def _preview_text(br_msg, count: int, target: str) -> str:
    snippet = ""
    if br_msg.text:
        snippet = br_msg.text.html[:200]
    elif br_msg.caption:
        snippet = br_msg.caption.html[:200]
    else:
        snippet = f"[{br_msg.media.value if br_msg.media else 'media'}]"

    label = "users" if target == "users" else "groups"
    return (
        f"📣 <b>Broadcast preview</b>\n\n"
        f"Recipients: <b>{count} {label}</b>\n"
        f"Message:\n\n{snippet}\n\n"
        f"Confirm to start sending. Estimated time: <b>{_estimate(count)}</b>."
    )


def _confirm_kb(broadcast_id: str, count: int, target: str) -> InlineKeyboardMarkup:
    label = "users" if target == "users" else "groups"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"✅ Send to {count} {label}", callback_data=f"bc_go_{broadcast_id}")],
        [InlineKeyboardButton("❌ Cancel", callback_data=f"bc_cancel_{broadcast_id}")],
    ])


@Client.on_message(filters.command("broadcast") & filters.user(OWNER_ID))
async def broadcast_cmd(bot, message):
    if not message.reply_to_message:
        return await message.reply("Reply to a message to broadcast it to all users.")

    _prune_pending()
    count, users = await get_users()
    broadcast_id = str(uuid.uuid4())[:8]
    _pending[broadcast_id] = {"msg": message.reply_to_message, "target": "users", "ts": time.time()}

    await message.reply(
        _preview_text(message.reply_to_message, count, "users"),
        reply_markup=_confirm_kb(broadcast_id, count, "users")
    )


@Client.on_message(filters.command("broadcast_groups") & filters.user(OWNER_ID))
async def broadcast_groups_cmd(bot, message):
    if not message.reply_to_message:
        return await message.reply("Reply to a message to broadcast it to all groups.")

    _prune_pending()
    count, groups = await get_groups()
    broadcast_id = str(uuid.uuid4())[:8]
    _pending[broadcast_id] = {"msg": message.reply_to_message, "target": "groups", "ts": time.time()}

    await message.reply(
        _preview_text(message.reply_to_message, count, "groups"),
        reply_markup=_confirm_kb(broadcast_id, count, "groups")
    )


@Client.on_callback_query(filters.regex(r"^bc_"))
async def broadcast_cb(bot, update):
    parts = update.data.split("_")
    action = parts[1]
    broadcast_id = parts[2]

    if action == "cancel":
        _pending.pop(broadcast_id, None)
        return await update.message.edit("❌ Broadcast cancelled.")

    pending = _pending.pop(broadcast_id, None)
    if not pending:
        return await update.message.edit("❌ Broadcast expired or already sent.")

    br_msg = pending["msg"]
    target = pending["target"]

    if target == "users":
        count, recipients = await get_users()
        ids = [r["_id"] for r in recipients]
        copy_fn = _copy_to
        del_fn = delete_user
    else:
        count, recipients = await get_groups()
        ids = [r["_id"] for r in recipients]
        copy_fn = _copy_to_group
        del_fn = delete_group

    status_msg = await update.message.edit(
        f"📤 Broadcasting to {count} {target}... 0 done."
    )

    success = failed = 0
    for i, chat_id in enumerate(ids):
        ok = await copy_fn(br_msg, chat_id)
        if ok:
            success += 1
        else:
            failed += 1
            try:
                await del_fn(chat_id)
            except Exception:
                pass
        if (i + 1) % 20 == 0:
            try:
                await status_msg.edit(
                    f"📤 Broadcasting... {i + 1}/{count} done. ✅ {success} ❌ {failed}"
                )
            except Exception:
                pass

    await status_msg.edit(
        f"✅ <b>Broadcast complete!</b>\n\n"
        f"Total: {count}\nSuccess: {success}\nFailed: {failed}"
    )
