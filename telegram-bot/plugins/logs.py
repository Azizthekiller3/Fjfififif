import sys
import time
import asyncio
import platform
import logging

from pyrogram import Client, filters
from pyrogram.types import Message

from config import OWNER_ID

logger = logging.getLogger(__name__)

_START_TIME = time.time()


def _uptime_str() -> str:
    delta = int(time.time() - _START_TIME)
    days, rem = divmod(delta, 86400)
    hours, rem = divmod(rem, 3600)
    mins, secs = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if mins:
        parts.append(f"{mins}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


async def _mongo_status() -> str:
    try:
        from database.database import _get_cols, _client
        _get_cols()
        await _client.admin.command("ping")
        return "✅ Connected"
    except Exception as e:
        return f"❌ {e}"


async def _session_status() -> str:
    try:
        from client import User
        if User.is_connected:
            me = await User.get_me()
            name = f"@{me.username}" if me.username else me.first_name
            return f"✅ {name}"
        return "⚠️ Not connected"
    except Exception as e:
        return f"❌ {e}"


def _mem_usage() -> str:
    try:
        import resource
        mem_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        mem_mb = mem_kb / 1024 if sys.platform != "darwin" else mem_kb / (1024 * 1024)
        return f"{mem_mb:.1f} MB"
    except Exception:
        return "N/A"


@Client.on_message(filters.command("logs") & filters.user(OWNER_ID))
async def logs_cmd(bot: Client, message: Message):
    msg = await message.reply("🔍 <b>Fetching status…</b>")

    import pyrogram

    mongo_st, session_st = await asyncio.gather(_mongo_status(), _session_status())

    try:
        from utils import get_users, get_groups, get_connected_channels_count
        u_count, _ = await get_users()
        g_count, _ = await get_groups()
        ch_count = await get_connected_channels_count()
        db_stats = (
            f"👥 <b>Users:</b> <code>{u_count}</code>\n"
            f"💬 <b>Groups:</b> <code>{g_count}</code>\n"
            f"📡 <b>Channels:</b> <code>{ch_count}</code>"
        )
    except Exception as e:
        db_stats = f"⚠️ Stats unavailable: {e}"

    text = (
        "📊 <b>Bot Status Report</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ <b>Uptime:</b> <code>{_uptime_str()}</code>\n"
        f"🗄 <b>MongoDB:</b> {mongo_st}\n"
        f"👤 <b>User Session:</b> {session_st}\n"
        f"🧠 <b>Memory:</b> <code>{_mem_usage()}</code>\n"
        f"🐍 <b>Python:</b> <code>{platform.python_version()}</code>\n"
        f"📦 <b>Pyrogram:</b> <code>{pyrogram.__version__}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{db_stats}"
    )

    await msg.edit(text)
