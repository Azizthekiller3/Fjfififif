import re
import asyncio
import logging
from time import time
from config import LOG_CHANNEL, BACKUP_CHANNEL
from utils import script, search_imdb, save_dlt_message, get_group, google_spell_check
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)

RESULTS_PER_PAGE = 10

_TITLE_PREFIX = re.compile(
    r'^[\U0001F300-\U0001FAFF\u2600-\u26FF\u2700-\u27BF\s]*'
    r'(?:TITLE\s*:\s*)?',
    re.IGNORECASE
)


def _get_user():
    try:
        from client import User
        return User if User.is_connected else None
    except Exception:
        return None


def _clean_name(raw: str) -> str:
    return _TITLE_PREFIX.sub("", raw).strip()


def _build_result_text(user_name: str, query: str, entries: list, page: int, total_pages: int) -> str:
    lines = [
        f"<b>Hey {user_name},</b>",
        f"<b>Here is the Results For: {query}</b>",
        "",
    ]
    for name, link in entries:
        lines.append(f"🟢 📗 <b>TITLE : {name}</b>")
        lines.append(f"🍿 <b>{link}</b>")
        lines.append("")
    lines.append(f"📄 <b>Page {page} / {total_pages}</b>")
    return "\n".join(lines)


def _nav_buttons(msg_id: str, page: int, total_pages: int) -> list:
    row = []
    if page > 1:
        row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"page_{msg_id}_{page - 1}"))
    row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        row.append(InlineKeyboardButton("Next ➡️", callback_data=f"page_{msg_id}_{page + 1}"))
    return row


def _join_button() -> list:
    return [InlineKeyboardButton("🔗 Join Backup Channel", url=BACKUP_CHANNEL)]


def _request_button(query: str) -> list:
    safe = query[:40].replace("_", "-")
    return [InlineKeyboardButton("📩 Request To Admin", callback_data=f"request_text_{safe}")]


async def _search_channels(user, channels: list, query: str) -> list:
    all_results = []
    for channel in channels:
        try:
            async for m in user.search_messages(chat_id=channel, query=query):
                try:
                    raw = (m.text or m.caption or "").split("\n")[0].strip()
                    name = _clean_name(raw)
                except Exception:
                    continue
                if not name:
                    continue
                entry = (name, m.link)
                if entry not in all_results:
                    all_results.append(entry)
        except FloodWait as e:
            logger.warning(f"FloodWait {e.value}s while searching channel {channel}")
            await asyncio.sleep(e.value)
        except Exception as e:
            logger.warning(f"Search error in channel {channel}: {e}")
    return all_results


@Client.on_message(
    filters.text & filters.group & filters.incoming
    & ~filters.command(["verify", "connect", "disconnect", "connections",
                        "fsub", "nofsub", "id", "stats", "broadcast",
                        "broadcast_groups", "start", "help", "about",
                        "autodelete"])
)
async def search(bot, message):
    try:
        ok = await bot.db_force_sub(message)
        if ok is False:
            return

        group = await get_group(message.chat.id)
        if not group:
            return
        channels = group.get("channels", [])
        if not channels:
            msg = await message.reply(
                "⚠️ <b>No channels connected yet.</b>\n\n"
                "Admin: use <code>/connect -100xxxxxxxxx</code> to link your movie channel."
            )
            await save_dlt_message(msg, int(time()) + 120)
            return
        if message.text.startswith("/"):
            return

        query = message.text
        user_name = message.from_user.first_name if message.from_user else "User"
        user = _get_user()

        if not user:
            msg = await message.reply("⚠️ <b>Search is temporarily unavailable. Please try again shortly.</b>")
            await save_dlt_message(msg, int(time()) + 60)
            return

        all_results = await _search_channels(user, channels, query)

        if not all_results:
            corrected = await google_spell_check(query)
            spell_movies = []
            if corrected:
                spell_movies = await search_imdb(corrected)

            if spell_movies:
                buttons = []
                for movie in spell_movies:
                    buttons.append([InlineKeyboardButton(
                        movie["title"],
                        callback_data=f"recheck_{movie['id']}"
                    )])
                buttons.append(_request_button(corrected))
                buttons.append(_join_button())
                msg = await message.reply(
                    f"<b>🔤 Spelling mistake!\nDid you mean: <i>{corrected}</i> ?\nChoose correct movie 👇</b>",
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
            else:
                movies = await search_imdb(query)
                if movies:
                    buttons = []
                    for movie in movies:
                        buttons.append([InlineKeyboardButton(
                            movie["title"],
                            callback_data=f"recheck_{movie['id']}"
                        )])
                    buttons.append(_request_button(query))
                    buttons.append(_join_button())
                    msg = await message.reply(
                        script.IMDB_FALLBACK,
                        reply_markup=InlineKeyboardMarkup(buttons)
                    )
                else:
                    msg = await message.reply(
                        "<b>🔴 No Results Found!</b>\n<b>Still no results found!</b>",
                        reply_markup=InlineKeyboardMarkup([
                            _request_button(query),
                            _join_button(),
                        ])
                    )
        else:
            total_pages = max(1, (len(all_results) + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE)
            page_entries = all_results[:RESULTS_PER_PAGE]
            text = _build_result_text(user_name, query, page_entries, 1, total_pages)

            markup_rows = []
            if total_pages > 1:
                markup_rows.append(_nav_buttons(str(message.id), 1, total_pages))
            markup_rows.append(_join_button())

            msg = await message.reply_text(
                text=text,
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup(markup_rows)
            )

        _time = int(time()) + group.get("auto_delete", 60)
        await save_dlt_message(msg, _time)
        await save_dlt_message(message, _time)
    except FloodWait as e:
        logger.warning(f"FloodWait {e.value}s in search handler")
        await asyncio.sleep(e.value)
    except Exception as e:
        logger.error(f"Search handler error: {e}", exc_info=True)


async def _db_force_sub(self, message):
    from database.db import force_sub
    return await force_sub(self, message)


Client.db_force_sub = _db_force_sub


@Client.on_callback_query(filters.regex(r"^recheck"))
async def recheck(bot, update):
    try:
        clicked = update.from_user.id
        try:
            typed = update.message.reply_to_message.from_user.id
        except Exception:
            return await update.message.delete()
        if clicked != typed:
            return await update.answer("This is not for you", show_alert=True)

        await update.message.edit("<b>🔍 Searching, please wait...</b>")
        imdb_id = update.data.split("_")[-1]
        results = await search_imdb(imdb_id)
        query = results[0]["title"] if results else imdb_id
        group = await get_group(update.message.chat.id)
        channels = group.get("channels", []) if group else []
        user_name = update.from_user.first_name if update.from_user else "User"
        user = _get_user()

        if not user:
            return await update.message.edit("⚠️ <b>Search is temporarily unavailable. Please try again shortly.</b>")

        all_results = await _search_channels(user, channels, query)

        if not all_results:
            return await update.message.edit(
                "<b>🔴 No Results Found!</b>\n<b>Still no results found!</b>",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📩 Request To Admin", callback_data=f"request_{imdb_id}")],
                    _join_button(),
                ])
            )

        total_pages = max(1, (len(all_results) + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE)
        page_entries = all_results[:RESULTS_PER_PAGE]
        text = _build_result_text(user_name, query, page_entries, 1, total_pages)

        markup_rows = []
        if total_pages > 1:
            markup_rows.append(_nav_buttons(str(update.message.id), 1, total_pages))
        markup_rows.append(_join_button())

        await update.message.edit(
            text=text,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(markup_rows)
        )
    except FloodWait as e:
        await asyncio.sleep(e.value)
    except Exception as e:
        logger.error(f"Recheck error: {e}", exc_info=True)
        try:
            await update.message.edit("⚠️ Something went wrong. Please try again.")
        except Exception:
            pass


@Client.on_callback_query(filters.regex(r"^request"))
async def request_to_admin(bot, update):
    try:
        clicked = update.from_user.id
        try:
            typed = update.message.reply_to_message.from_user.id
        except Exception:
            return await update.message.delete()
        if clicked != typed:
            return await update.answer("This is not for you", show_alert=True)

        parts = update.data.split("_", 2)

        if len(parts) >= 2 and parts[1] == "text":
            name = parts[2] if len(parts) > 2 else "Unknown"
            url = ""
        else:
            imdb_id = parts[1] if len(parts) > 1 else ""
            results = await search_imdb(imdb_id)
            name = results[0]["title"] if results else imdb_id
            url = f"https://www.imdb.com/title/tt{imdb_id}" if imdb_id else ""

        group = await get_group(update.message.chat.id)
        admin = group.get("user_id") if group else None

        text = f"#RequestFromYourGroup\n\n{name}"
        if url:
            text += f"\n{url}"

        if admin:
            try:
                await bot.send_message(chat_id=admin, text=text, disable_web_page_preview=True)
            except Exception:
                pass
        if LOG_CHANNEL:
            try:
                await bot.send_message(chat_id=LOG_CHANNEL, text=text, disable_web_page_preview=True)
            except Exception:
                pass

        await update.answer("Request Sent To Admin ✅", show_alert=True)

        asyncio.create_task(_delayed_delete(update.message, 60))
    except Exception as e:
        logger.error(f"Request handler error: {e}", exc_info=True)


async def _delayed_delete(message, delay: int):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass


@Client.on_callback_query(filters.regex(r"^noop$"))
async def noop_cb(bot, update):
    await update.answer()
