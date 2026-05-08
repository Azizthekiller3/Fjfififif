# 🎬 MovieBot

A Telegram post-search bot. Add it to a group, link your channel, and members can search for movies just by typing the name.

---

## Quick deploy

### Railway (recommended)
1. Fork this repo
2. Create a new project on [railway.app](https://railway.app) → **Deploy from GitHub repo** → select your fork
3. Set **Root Directory** to `telegram-bot` and **Dockerfile** to `telegram-bot/Dockerfile`
4. Add all environment variables from the table below
5. Deploy — Railway auto-restarts on crash and redeploys on every git push

### VPS / any server
```bash
git clone https://github.com/YOUR_USERNAME/Fjfififif.git
cd Fjfififif/telegram-bot
cp .env.example .env
# fill in .env values
pip install -r requirements.txt
python bot.py
```

### Docker
```bash
cd telegram-bot
docker build -t moviebot .
docker run -d --env-file .env --restart always moviebot
```

---

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `BOT_TOKEN` | ✅ | From [@BotFather](https://t.me/BotFather) |
| `API_ID` | ✅ | Integer from [my.telegram.org](https://my.telegram.org) |
| `API_HASH` | ✅ | String from [my.telegram.org](https://my.telegram.org) |
| `OWNER_ID` | ✅ | Your Telegram numeric user ID (get from [@userinfobot](https://t.me/userinfobot)) |
| `MONGODB_PASSWORD` | ✅ | Password for your MongoDB Atlas cluster |
| `SESSION_SECRET` | ✅ | Pyrogram user session string — see below |
| `LOG_CHANNEL` | optional | Channel ID (e.g. `-100123456789`) for start/stop logs |
| `UPDATES_CHANNEL` | optional | Public channel username shown in bot profile |
| `BACKUP_CHANNEL` | optional | Backup channel link shown in search results |
| `PORT` | optional | Health-check port (set automatically by Railway/Render/Heroku) |

---

## Generating SESSION_SECRET

The bot needs a **real Telegram user account** session to join channels and search posts.

1. Deploy the bot with all other variables set
2. Visit `https://<your-deployment-url>/gen` in a browser
3. Enter your phone number and the OTP Telegram sends you
4. Copy the session string that appears
5. Add it as `SESSION_SECRET` in your environment variables
6. Redeploy

> Keep this value private — it gives full access to that Telegram account.

---

## MongoDB setup

1. Create a free cluster on [MongoDB Atlas](https://cloud.mongodb.com)
2. Create a database user with a password
3. Allow connections from anywhere (`0.0.0.0/0`) in Network Access
4. Set `MONGODB_PASSWORD` to that user's password

The bot automatically creates two databases:
- `Channel-Filter` — groups, users, auto-delete records
- `PostSearchBot` — indexed post/file records for search

---

## Bot commands

| Command | Description |
|---|---|
| `/start` | Check if bot is alive |
| `/help` | Show all commands |
| `/verify` | Register a group (send in group first) |
| `/connect <channel_id>` | Link a channel to search from |
| `/disconnect <channel_id>` | Unlink a channel |
| `/connections` | List connected channels |
| `/fsub <channel_id>` | Set force-subscribe channel |
| `/nofsub` | Remove force-subscribe |
| `/autodelete <seconds>` | Auto-delete search results after N seconds |
| `/id` | Get chat/channel ID |
| `/ping` | Check bot response speed |
| `/logs` | Owner only — live status report |

---

## Architecture

```
bot.py          — entry point, Bot class, keepalive task, auto-delete task
config.py       — all env var parsing
client.py       — user session client (for search/join)
health.py       — Flask health-check server (/health) + session generator (/gen)
patches.py      — safe no-op compatibility shim
plugins/        — all command handlers (auto-loaded by Pyrogram)
database/
  db.py         — groups, users, auto-delete (Channel-Filter DB)
  database.py   — file/post index for search (PostSearchBot DB)
utils/          — IMDB lookup, spell check, message helpers
```

**Key design decisions:**
- Auto-delete runs as an `asyncio` task inside the main process — never as a subprocess — to avoid the dual-token update-stealing bug
- Bot session uses `in_memory=True` — no SQLite file to corrupt across restarts
- Keepalive ping every 4 minutes keeps the MTProto TCP connection alive past Railway's ~5 min idle timeout
- `os._exit(1)` after 3 consecutive keepalive failures forces Railway to do a clean restart
- `from client import User` is lazy (inside handlers) in `connect.py` so the plugin loads even when the user session is down

---

## Health check

The bot exposes a health endpoint that platforms use to verify it's running:

```
GET /health  →  200 OK
```
