# main.py
import asyncio
import json
import logging
import os
from datetime import datetime
from functools import wraps
from typing import Any, Dict

import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, Router, types
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery, FSInputFile
from dotenv import load_dotenv

from database import (
    init_db, add_user, update_user, get_user, get_all_users, get_recent_users, get_user_lookups,
    get_leaderboard, get_inactive_users, get_total_stats, get_daily_stats, get_lookup_stats,
    add_lookup, increment_daily_stat, is_banned, ban_user, unban_user, delete_user,
    is_admin, add_admin, remove_admin, get_all_admins, search_user
)

load_dotenv()

OWNER_ID = 8104850843
CHANNEL1_ID = -1003090922367
CHANNEL1_URL = "https://t.me/all_data_here"
CHANNEL2_ID = -1003698567122
CHANNEL2_URL = "https://t.me/osint_lookup"
TOKEN = os.getenv("TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_PATH = "/webhook"
PORT = int(os.getenv("PORT", 8080))

bot = Bot(TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

logging.basicConfig(level=logging.INFO)

GLOBAL_REMOVES = [
    "@patelkrish_99", "patelkrish_99", "t.me/anshapi", "anshapi",
    "@Kon_Hu_Mai", "Dm to buy access", "dm to buy access", "Kon_Hu_Mai"
]
NUM_EXTRA_REMOVES = [
    "dm to buy", "owner", "@kon_hu_mai",
    "Ruk ja bhencho itne m kya unlimited request lega?? Paid lena h to bolo 100-400₹ @Simpleguy444"
]

LOG_CHANNELS = {
    "NUM": -1003482423742,
    "ADR": -1003482423742,
    "IFSC": -1003624886596,
    "EMAIL": -1003431549612,
    "GST": -1003634866992,
    "VEHICLE": -1003237155636,
    "PIN": -1003677285823,
    "INSTA": -1003498414978,
    "GIT": -1003576017442,
    "PAK": -1003663672738,
    "IP": -1003665811220,
    "FFINFO": -1003588577282,
    "FFBAN": -1003521974255,
    "TG2NUM": -1003642820243,
    "VCHALAN": -1003237155636,
    "TGINFO": -1003643170105,
    "TGINFOPRO": -1003643170105
}

COMMANDS = {
    "num": {"url": "https://num-free-rootx-jai-shree-ram-14-day.vercel.app/?key=lundkinger&number={query}", "log": "NUM", "extra_clean": True},
    "adr": {"url": "https://api-ij32.onrender.com/aadhar?match={query}", "log": "ADR", "extra_clean": False},
    "tg2num": {"url": "https://tg2num-owner-api.vercel.app/?userid={query}", "log": "TG2NUM", "extra_clean": False},
    "vehicle": {"url": "https://vehicle-info-aco-api.vercel.app/info?vehicle={query}", "log": "VEHICLE", "extra_clean": False},
    "vchalan": {"url": "https://api.b77bf911.workers.dev/vehicle?registration={query}", "log": "VCHALAN", "extra_clean": False},
    "ip": {"url": "https://abbas-apis.vercel.app/api/ip?ip={query}", "log": "IP", "extra_clean": False},
    "email": {"url": "https://abbas-apis.vercel.app/api/email?mail={query}", "log": "EMAIL", "extra_clean": False},
    "ffinfo": {"url": "https://official-free-fire-info.onrender.com/player-info?key=DV_M7-INFO_API&uid={query}", "log": "FFINFO", "extra_clean": False},
    "ffban": {"url": "https://abbas-apis.vercel.app/api/ff-ban?uid={query}", "log": "FFBAN", "extra_clean": False},
    "pin": {"url": "https://api.postalpincode.in/pincode/{query}", "log": "PIN", "extra_clean": False},
    "ifsc": {"url": "https://abbas-apis.vercel.app/api/ifsc?ifsc={query}", "log": "IFSC", "extra_clean": False},
    "gst": {"url": "https://api.b77bf911.workers.dev/gst?number={query}", "log": "GST", "extra_clean": False},
    "insta": {"url": "https://mkhossain.alwaysdata.net/instanum.php?username={query}", "log": "INSTA", "extra_clean": False},
    "tginfo": {"url": "https://openosintx.vippanel.in/tgusrinfo.php?key=OpenOSINTX-FREE&user={query}", "log": "TGINFO", "extra_clean": False},
    "tginfopro": {"url": "https://api.b77bf911.workers.dev/telegram?user={query}", "log": "TGINFOPRO", "extra_clean": False},
    "git": {"url": "https://abbas-apis.vercel.app/api/github?username={query}", "log": "GIT", "extra_clean": False},
    "pak": {"url": "https://abbas-apis.vercel.app/api/pakistan?number={query}", "log": "PAK", "extra_clean": False}
}

class BroadcastForm(StatesGroup):
    message = State()

class BulkDMForm(StatesGroup):
    ids = State()
    message = State()

class AccessMiddleware:
    async def __call__(self, handler, event: Message, data: Dict[str, Any]):
        if event.chat.type == "private":
            user_id = event.from_user.id
            if user_id != OWNER_ID and not await is_admin(user_id):
                await event.reply("Ye bot sirf group me kaam karta hai.\nPersonal use ke liye use kare: @osintfatherNullBot")
                return
        else:
            user_id = event.from_user.id
            if await is_banned(user_id):
                await event.reply("You are banned.")
                return
            if user_id != OWNER_ID and not await is_admin(user_id):
                joined1 = await check_member(CHANNEL1_ID, user_id)
                joined2 = await check_member(CHANNEL2_ID, user_id)
                if not joined1 or not joined2:
                    kb = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton("Join Channel 1", url=CHANNEL1_URL)],
                        [InlineKeyboardButton("Join Channel 2", url=CHANNEL2_URL)],
                        [InlineKeyboardButton("Retry", callback_data="retry_join")]
                    ])
                    await event.reply("Please join both channels to use the bot.", reply_markup=kb)
                    return
        await handler(event, data)

router.message.middleware(AccessMiddleware())

async def check_member(chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ("member", "administrator", "creator")
    except (TelegramForbiddenError, Exception):
        return False

def admin_required(func):
    @wraps(func)
    async def wrapper(message: Message, *args, **kwargs):
        user_id = message.from_user.id
        if user_id == OWNER_ID or await is_admin(user_id):
            return await func(message, *args, **kwargs)
        else:
            await message.reply("You are not authorized.")
    return wrapper

def owner_required(func):
    @wraps(func)
    async def wrapper(message: Message, *args, **kwargs):
        if message.from_user.id == OWNER_ID:
            return await func(message, *args, **kwargs)
        else:
            await message.reply("You are not the owner.")
    return wrapper

def clean_branding(data: Any, extra: bool = False) -> Any:
    str_data = json.dumps(data) if isinstance(data, (dict, list)) else str(data)
    removes = GLOBAL_REMOVES.copy()
    if extra:
        removes.extend(NUM_EXTRA_REMOVES)
    for r in removes:
        str_data = str_data.replace(r, "")
    try:
        return json.loads(str_data)
    except json.JSONDecodeError:
        return {"response": str_data}

async def fetch_api(url: str, retries: int = 3, backoff: int = 1) -> Dict:
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        for attempt in range(retries):
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        text = await response.text()
                        try:
                            return json.loads(text)
                        except json.JSONDecodeError:
                            return {"response": text}
            except Exception:
                await asyncio.sleep(backoff * (2 ** attempt))
        return {"error": "API request failed"}

async def log_to_channel(cmd: str, data: Dict, user_id: int, query: str, group_id: int):
    channel_id = LOG_CHANNELS.get(cmd.upper())
    if channel_id:
        text = f"User ID: {user_id}\nGroup ID: {group_id}\nQuery: {query}\nResult:\n{json.dumps(data, indent=2)}"
        try:
            await bot.send_message(channel_id, text)
        except Exception:
            pass

async def send_result(message: Message, data: Dict, query: str):
    html = f'<pre>{json.dumps(data, indent=2)}</pre>\ndeveloper: @Nullprotocol_X\npowered_by: NULL PROTOCOL'
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("Copy", callback_data="copy_result")],
        [InlineKeyboardButton("Search", switch_inline_query_current_chat=query)]
    ])
    await message.reply(html, parse_mode=ParseMode.HTML, reply_markup=kb)

def create_command_handler(cmd: str):
    async def handler(message: Message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply(f"Usage: /{cmd} <query>")
            return
        query = args[1].strip()
        if not query:
            await message.reply(f"Invalid query for /{cmd}")
            return
        user_id = message.from_user.id
        now = datetime.utcnow().isoformat()
        if not await get_user(user_id):
            await add_user(user_id, now, now, 0)
        else:
            await update_user(user_id, now, 1)
        config = COMMANDS[cmd]
        url = config["url"].format(query=query)
        data = await fetch_api(url)
        if "error" in data:
            await message.reply("Error fetching data. Please try again later.")
            return
        cleaned = clean_branding(data, config["extra_clean"])
        await send_result(message, cleaned, query)
        await log_to_channel(config["log"], data, user_id, query, message.chat.id)
        await add_lookup(user_id, cmd, query, json.dumps(data), now)
        await increment_daily_stat(now[:10], cmd)
    return handler

for cmd in COMMANDS:
    router.message(Command(cmd))(create_command_handler(cmd))

@router.callback_query(lambda c: c.data == "retry_join")
async def retry_join(callback: CallbackQuery):
    user_id = callback.from_user.id
    joined1 = await check_member(CHANNEL1_ID, user_id)
    joined2 = await check_member(CHANNEL2_ID, user_id)
    if joined1 and joined2:
        await callback.message.edit_text("Joined successfully. You can now use the bot.")
    else:
        await callback.answer("Please join both channels.", show_alert=True)

@router.callback_query(lambda c: c.data == "copy_result")
async def copy_result(callback: CallbackQuery):
    await callback.answer("Result copied to clipboard. (Simulated)", show_alert=True)

@router.message(Command("broadcast"))
@admin_required
async def broadcast_start(message: Message, state: FSMContext):
    await message.reply("Please reply with the message to broadcast (text, photo, video, etc.).")
    await state.set_state(BroadcastForm.message)

@router.message(BroadcastForm.message)
@admin_required
async def broadcast_process(message: Message, state: FSMContext):
    users = await get_all_users()
    success = 0
    for user_id in users:
        try:
            await bot.copy_message(user_id, message.chat.id, message.message_id)
            success += 1
            await asyncio.sleep(0.1)
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
        except Exception:
            pass
    await message.reply(f"Broadcast sent to {success} users.")
    await state.clear()

@router.message(Command("dm"))
@admin_required
async def dm(message: Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.reply("Usage: /dm <user_id> <text>")
        return
    try:
        user_id = int(args[1])
        text = args[2]
        await bot.send_message(user_id, text)
        await message.reply("DM sent.")
    except Exception:
        await message.reply("Failed to send DM.")

@router.message(Command("bulkdm"))
@admin_required
async def bulkdm_start(message: Message, state: FSMContext):
    await message.reply("Send comma-separated user IDs.")
    await state.set_state(BulkDMForm.ids)

@router.message(BulkDMForm.ids)
@admin_required
async def bulkdm_ids(message: Message, state: FSMContext):
    await state.update_data(ids=message.text)
    await message.reply("Now reply with the message to send.")
    await state.set_state(BulkDMForm.message)

@router.message(BulkDMForm.message)
@admin_required
async def bulkdm_process(message: Message, state: FSMContext):
    data = await state.get_data()
    ids_str = data["ids"]
    user_ids = [int(uid.strip()) for uid in ids_str.split(",") if uid.strip().isdigit()]
    success = 0
    for user_id in user_ids:
        try:
            await bot.copy_message(user_id, message.chat.id, message.message_id)
            success += 1
            await asyncio.sleep(0.1)
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
        except Exception:
            pass
    await message.reply(f"Bulk DM sent to {success} users.")
    await state.clear()

@router.message(Command("ban"))
@admin_required
async def ban(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Usage: /ban <user_id>")
        return
    try:
        user_id = int(args[1])
        await ban_user(user_id)
        await message.reply("User banned.")
    except Exception:
        await message.reply("Failed to ban.")

@router.message(Command("unban"))
@admin_required
async def unban(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Usage: /unban <user_id>")
        return
    try:
        user_id = int(args[1])
        await unban_user(user_id)
        await message.reply("User unbanned.")
    except Exception:
        await message.reply("Failed to unban.")

@router.message(Command("deleteuser"))
@admin_required
async def deleteuser(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Usage: /deleteuser <user_id>")
        return
    try:
        user_id = int(args[1])
        await delete_user(user_id)
        await message.reply("User deleted.")
    except Exception:
        await message.reply("Failed to delete.")

@router.message(Command("searchuser"))
@admin_required
async def searchuser(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Usage: /searchuser <query>")
        return
    query = args[1]
    results = await search_user(query)
    if results:
        text = "\n".join([f"ID: {r[0]}, First: {r[1]}, Last: {r[2]}, Lookups: {r[3]}" for r in results])
        await message.reply(text)
    else:
        await message.reply("No results.")

@router.message(Command("users"))
@admin_required
async def users(message: Message):
    total = await get_total_stats()
    await message.reply(f"Total users: {total['users']}")

@router.message(Command("recentusers"))
@admin_required
async def recentusers(message: Message):
    users = await get_recent_users(10)
    text = "\n".join([f"ID: {u[0]}, Last: {u[2]}" for u in users])
    await message.reply(text or "No recent users.")

@router.message(Command("userlookups"))
@admin_required
async def userlookups(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Usage: /userlookups <user_id>")
        return
    try:
        user_id = int(args[1])
        lookups = await get_user_lookups(user_id)
        text = "\n".join([f"{l[1]}: {l[2]} at {l[4]}" for l in lookups])
        await message.reply(text or "No lookups.")
    except Exception:
        await message.reply("Failed.")

@router.message(Command("leaderboard"))
@admin_required
async def leaderboard(message: Message):
    leaders = await get_leaderboard(10)
    text = "\n".join([f"ID: {l[0]}, Lookups: {l[1]}" for l in leaders])
    await message.reply(text or "No data.")

@router.message(Command("inactiveusers"))
@admin_required
async def inactiveusers(message: Message):
    inactives = await get_inactive_users()
    text = "\n".join([f"ID: {i[0]}, Last: {i[1]}" for i in inactives])
    await message.reply(text or "No inactive users.")

@router.message(Command("stats"))
@admin_required
async def stats(message: Message):
    s = await get_total_stats()
    text = f"Users: {s['users']}\nLookups: {s['lookups']}"
    await message.reply(text)

@router.message(Command("dailystats"))
@admin_required
async def dailystats(message: Message):
    ds = await get_daily_stats()
    text = "\n".join([f"{d[0]}: {d[1]}" for d in ds])
    await message.reply(text or "No data.")

@router.message(Command("lookupstats"))
@admin_required
async def lookupstats(message: Message):
    ls = await get_lookup_stats()
    text = "\n".join([f"{l[0]}: {l[1]}" for l in ls])
    await message.reply(text or "No data.")

@router.message(Command("addadmin"))
@owner_required
async def addadmin(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Usage: /addadmin <user_id>")
        return
    try:
        user_id = int(args[1])
        await add_admin(user_id)
        await message.reply("Admin added.")
    except Exception:
        await message.reply("Failed.")

@router.message(Command("removeadmin"))
@owner_required
async def removeadmin(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Usage: /removeadmin <user_id>")
        return
    try:
        user_id = int(args[1])
        await remove_admin(user_id)
        await message.reply("Admin removed.")
    except Exception:
        await message.reply("Failed.")

@router.message(Command("listadmins"))
@owner_required
async def listadmins(message: Message):
    admins = await get_all_admins()
    text = "\n".join([str(a[0]) for a in admins])
    await message.reply(text or "No admins.")

@router.message(Command("settings"))
@owner_required
async def settings(message: Message):
    await message.reply("No settings available.")

@router.message(Command("fulldbbackup"))
@owner_required
async def fulldbbackup(message: Message):
    await bot.send_document(message.chat.id, FSInputFile("bot.db"))

async def health(request):
    return web.Response(text="Bot running")

async def handle_webhook(request):
    update = types.Update(**await request.json())
    await dp.process_update(update)
    return web.Response()

async def on_startup(app):
    await init_db()
    await add_admin(OWNER_ID)
    await add_admin(5987905091)
    webhook = f"{WEBHOOK_URL}{WEBHOOK_PATH}"
    await bot.set_webhook(webhook)

async def on_shutdown(app):
    await bot.delete_webhook()

app = web.Application()
app.add_routes([web.get("/", health), web.post(WEBHOOK_PATH, handle_webhook)])
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

if __name__ == "__main__":
    web.run_app(app, port=PORT)
