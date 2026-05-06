# Post Search Bot

A Pyrogram-based Telegram bot that lets group members search for movies/content by typing in a group. The bot searches connected channels and returns direct message links.

## Run & Operate

- `cd telegram-bot && python bot.py` — run the Telegram bot (port 5000)
- `pnpm --filter @workspace/api-server run dev` — run the API server (port 5000)
- `pnpm run typecheck` — full typecheck across all packages
- Workflow: `Telegram Bot` (console, port 5000)

Required secrets:
- `BOT_TOKEN` — Telegram bot token (from @BotFather)
- `API_ID` — Telegram API ID (from my.telegram.org)
- `API_HASH` — Telegram API hash (from my.telegram.org)
- `OWNER_ID` — Owner's Telegram user ID
- `LOG_CHANNEL` — Log channel ID (integer, e.g. -100xxxxxxxxx)
- `MONGODB_PASSWORD` — MongoDB Atlas password (builds URI automatically)
- `SESSION` — Pyrogram user session string (needed for search; generate at /gen)

## Stack

- Python 3.11, Pyrogram 2.0.106, Motor (async MongoDB), Flask (health + session generator)
- MongoDB Atlas for group/user/auto-delete storage
- cinemagoer (imdb module) for IMDb fallback search
- pnpm workspaces, Node.js 24, TypeScript 5.9 (API server side)

## Where things live

```
telegram-bot/
  bot.py            — main entry, Bot class
  config.py         — all env var loading
  client.py         — User + DlBot Pyrogram clients
  health.py         — Flask health server + /gen session generator UI
  plugins/          — all bot command handlers
    search.py       — core movie search + pagination
    misc.py         — /start /help /about /id /stats
    connect.py      — /connect /disconnect /connections
    fsub.py         — /fsub /nofsub + checksub callback
    verify.py       — /verify + approve/decline callbacks
    newgroup.py     — handles bot being added to groups
    broadcast.py    — /broadcast /broadcast_groups
    autodelete.py   — /autodelete timer setting
  utils/
    script.py       — all message templates
    imdb.py         — IMDb search via cinemagoer
    spell.py        — Google spell-check
    delete.py       — auto-delete worker subprocess
    helpers.py      — shared Pyrogram helpers
  database/
    db.py           — groups, users, auto-delete collections (Channel-Filter DB)
    database.py     — files, users, groups collections (PostSearchBot DB)
```

## Architecture decisions

- Bot uses Pyrogram `plugins` system — each file in `plugins/` auto-loads handlers
- User session (SESSION) needed for `search_messages` — bot token alone can't search channel history
- Auto-delete worker runs as a separate subprocess with its own Pyrogram client
- Health server runs on Flask in a background thread alongside the async bot
- MONGODB_PASSWORD builds the full MongoDB Atlas URI automatically
- Session generator UI at `/gen` — web form to generate Pyrogram session strings

## Product

- Users type a movie/show name in a group → bot searches connected channels → returns direct links
- Group admins connect their channels with `/connect -100xxxxxxxxx`
- Force-subscribe: restrict users from chatting until they join a channel (`/fsub`)
- Auto-delete: search results auto-delete after 1/2/5 minutes (`/autodelete`)
- Owner can broadcast messages to all users or groups
- Groups require owner verification before use (`/verify`)
- IMDb fallback + Google spell-check when no local results found

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

- SESSION must be a valid Pyrogram session string — generate one at `/gen` on the health server
- Without SESSION, search is disabled (bot only has bot-token, can't call search_messages)
- `cinemagoer` package installs as the `imdb` module (not `cinemagoer`)
- Bot must be run from inside the `telegram-bot/` directory (`cd telegram-bot && python bot.py`)

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
