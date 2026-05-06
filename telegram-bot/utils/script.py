class script:
    START = """👋 Hey {},

✅ I'm Alive And Running!

I Am A Post Search Bot — Add Me To Your Group And Link Your Channel. Members Can Then Search For Movies Just By Typing The Name.

<b>Send /help For All Commands</b>"""

    HELP = """<b>‼️  Commands  ‼️</b>

/start - Check If I'm Alive or Not!
/id - Get Channel/Group Id
/verify - Send in group & wait for It To Accept
/connect - Link Database Channel/Group to search from
/disconnect - Disconnect Database
/fsub - Add a Force Subscribe Channel
/nofsub - Remove Force Subscribe Channel
/connections - Get connected channels list
/autodelete - Set auto-delete timer (1, 2 or 5 minutes)

<b>How To Setup:</b>

❂ Add Me As Admin In Your Group And Channel.
❂ Type /verify In Group.
❂ Wait Until Your Request Is Approved.
❂ Use <code>/connect -100xxxxxxxxxx</code> To Link Your Channel."""

    ABOUT = """<b>➣ My Name ⋟  {}</b>
<b>➢ Language ⋟  <a href="https://www.python.org">Python 3</a></b>
<b>➣ Database ⋟  <a href="https://www.mongodb.com">Mongo DB</a></b>
<b>➢ Framework ⋟  <a href="https://docs.pyrogram.org">Pyrogram</a></b>"""

    STATS = """<b>📊 Bot Statistics</b>

👤 <b>Total Users :</b> {}
♻️ <b>Total Groups :</b> {}
📡 <b>Connected Channels :</b> {}"""

    BROADCAST = """<u>{}</u>

Total: {}
Remaining: {}
Success: {}
Failed: {}"""

    IMDB_FALLBACK = "<b>I couldn't find anything related to that.\nDid you mean any one of these ??</b>"

    IMDB_RECHECK = "<b>🔍 Searched with corrected spelling — take care next time 😋</b>\n\n"

    NO_RESULTS_FINAL = "<b>⚠️ No Results Found !!\nPlease request the group admin 👇🏻</b>"

    FSUB_MSG = "<b>🚫 Hi Dear {}!\n\nTo send messages in this group you must first join our channel 💯</b>"

    BANNED_MSG = "Sorry {}!\nYou are banned from our channel, you will be banned from here within 10 seconds"

    WELCOME = """<b>☤ Thank You For Adding Me In {}

• Don't Forget To Make Me Admin

• Please Get Access By /verify Command

• If You Have Any Doubt You Can Clear It Using Below Buttons</b>"""

    APPROVE_PHOTO = "https://telegra.ph/file/a706afc296de6da2a40c8.jpg"

    APPROVE_MSG = "<b>Your Verification Request For {} Has Been Approved ✅</b>"

    DECLINE_MSG = "Your verification request for {} has been declined 😐 Please Contact Admin"

    VERIFY_SENT = "Verification Request Sent ✅\nCheck Your PM With Me To Approve"

    PM_REPLY = """<b>Hy,

If You Want Movies / Series Then Add Me To Your Group And Use /verify</b>"""
