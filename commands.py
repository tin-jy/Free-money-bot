from telegram import Update
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown
from datetime import datetime, timedelta, timezone
from collections import deque
import logic
import html
from constants import *
import random
import asyncio
from collections import defaultdict

pending_takes = set()
user_locks = defaultdict(asyncio.Lock)

last_sent = {}

recent_messages = deque(maxlen=10)
sample = {
    "combo": 0,
    "last_sent": datetime.now(timezone.utc)
}
recent_stickers = {
    "lookie_stickers": sample.copy(),
    "good_stickers": sample.copy(),
    "angry_stickers": sample.copy()
}

async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'Hello {update.effective_user.first_name}')

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    response = f"Use /geiwoqian to get credits! Users get 3 attempts weekly that reset every Saturday at 8pm SGT. Bank top-ups are done daily at 8pm SGT."
    await update.message.reply_text(response)

async def bad(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_sticker(
        chat_id=update.effective_chat.id,
        sticker=random.choice(BAD_STICKERS),
        reply_to_message_id=update.message.id
    )

async def good(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_sticker(
        chat_id=update.effective_chat.id,
        sticker=random.choice(GOOD_STICKERS),
        reply_to_message_id=update.message.id
    )

async def process_take_status(update: Update, context: ContextTypes.DEFAULT_TYPE, take_status, amount):
    if take_status == UNEXPECTED_ERROR:
        await update.message.reply_text(UNEXPECTED_ERROR_MESSAGE)
    elif take_status == USER_DUMB:
        await context.bot.send_sticker(
            chat_id=update.effective_chat.id,
            sticker=random.choice(CONFUSION_STICKERS),
            reply_to_message_id=update.message.id
        )   
    elif take_status == USER_GREEDY:
        if roll_chance(25):
            await context.bot.send_sticker(
                chat_id=update.effective_chat.id,
                sticker=random.choice(LAUGH_STICKERS),
                reply_to_message_id=update.message.id
            )
        await update.message.reply_text(USER_GREEDY_MESSAGE)
    elif take_status == USER_SUCCESS:
        if amount >= success_threshold:
            await context.bot.send_sticker(
                chat_id=update.effective_chat.id,
                sticker=random.choice(COGRATULATIONS_STICKERS),
                reply_to_message_id=update.message.id
                )
            await update.message.reply_text(f"🎉🎉🎉 {update.effective_user.name} took {amount}! 🎉🎉🎉")
        else:
            await update.message.reply_text(f"🎉 {update.effective_user.name} took {amount} 🎉")

async def take(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    args = context.args

    logic.create_user_if_not_exist(user.id, user.name)
    logic.top_up_bank()
    logic.reset_user_attempts()

    attempts_remaining = logic.get_remaining_attempts(user.id)
    assert attempts_remaining >= 0
    if attempts_remaining == 0:
        logic.log_take_attempt(
            user_id=user.id,
            user_name=user.name,
            chat_id=update.effective_chat.id,
            chat_type=update.effective_chat.type,
            amount=0,
            is_successful=False,
            reason="No attempts"
        )
        await update.message.reply_text(NO_MORE_ATTEMPTS_MESSAGE)
        return

    if args:
        try:
            amount = int(args[0])
        except ValueError:
            await update.message.reply_text(INVALID_VALUE_ERROR_MESSAGE)
            return
        take_status = logic.take(user.id, amount)

        logic.log_take_attempt(
            user_id=user.id,
            user_name=user.name,
            chat_id=update.effective_chat.id,
            chat_type=update.effective_chat.type,
            amount=amount,
            is_successful=(take_status == USER_SUCCESS),
            reason="None" if take_status == USER_SUCCESS else "Stupid" if take_status == USER_DUMB else "Greedy"
        )
        
        await process_take_status(update, context, take_status, amount)
        return

    await update.message.reply_text(AMOUNT_QUERY)
    pending_takes.add(user.id)

def is_not_recent(key, delay=5):
    return key not in last_sent or last_sent[key] + timedelta(minutes=delay) < datetime.now(timezone.utc)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text

    async with user_locks[user.id]:
        if user.id in pending_takes:
            try:
                amount = int(text)
            except ValueError:
                pending_takes.remove(user.id)
                return

            pending_takes.remove(user.id)

            take_status = logic.take(user.id, amount)

            logic.log_take_attempt(
                user_id=user.id,
                user_name=user.name,
                chat_id=update.effective_chat.id,
                chat_type=update.effective_chat.type,
                amount=amount,
                is_successful=(take_status == USER_SUCCESS),
                reason="None" if take_status == USER_SUCCESS else "Stupid" if take_status == USER_DUMB else "Greedy"
            )
            await process_take_status(update, context, take_status, amount)
            return

    text = text.lower()
    if "dataa" in text or "huaidan" in text:
        key = "whack"
        if is_not_recent(key):
            await context.bot.send_sticker(
                chat_id=update.effective_chat.id,
                sticker=random.choice(WHACK_STICKERS)
            )
            last_sent[key] = datetime.now(timezone.utc)
    elif text == "sad":
        key = "sad"
        if is_not_recent(key):
            await context.bot.send_sticker(
                chat_id=update.effective_chat.id,
                sticker=random.choice(SAD_STICKERS)
            )
            last_sent[key] = datetime.now(timezone.utc)
    elif "have no proo" in text or "meiyou proo" in text:
        key = "proof"
        if is_not_recent(key):
            await context.bot.send_sticker(
                chat_id=update.effective_chat.id,
                sticker=random.choice(PROOF_STICKERS)
            )
            last_sent[key] = datetime.now(timezone.utc)
    elif ("peppercorn" in text or "hangyodon" in text) and user.id != ADMIN_ID:
        key = "peppercorn"
        if is_not_recent(key):
            await context.bot.send_sticker(
                chat_id=update.effective_chat.id,
                sticker=random.choice(PEPPERCORN_STICKERS)
            )
            last_sent[key] = datetime.now(timezone.utc)
    elif "chini" in text:
        key = "chini"
        if is_not_recent(key):
            await context.bot.send_sticker(
                chat_id=update.effective_chat.id,
                sticker=random.choice(CHINI_STICKERS)
            )
            last_sent[key] = datetime.now(timezone.utc)
    elif "woyao" in text or "woyeyao" in text or "wodene" in text:
        key = "woyao"
        if is_not_recent(key) and roll_chance(50):
            await context.bot.send_sticker(
                chat_id=update.effective_chat.id,
                sticker=random.choice(WOYAO_STICKERS)
            )
            last_sent[key] = datetime.now(timezone.utc)
    elif text.startswith("i'm ") or text.startswith("im "):
        remaining = " ".join(text.split()[1:])
        if remaining and roll_chance(25):
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Hi {remaining}".upper()
            )
    elif text.startswith("hi "):
        remaining = " ".join(text.split()[1:])
        with_apostrophe = f"i'm {remaining}"
        without_apostrophe = f"im {remaining}"
        if with_apostrophe in recent_messages or without_apostrophe in recent_messages:
            key = "laugh"
            if is_not_recent(key, delay=1):
                await context.bot.send_sticker(
                    chat_id=update.effective_chat.id,
                    sticker=random.choice(LAUGH_STICKERS)
                )
                last_sent[key] = datetime.now(timezone.utc)
    elif "cole joke" in text:
        for message in recent_messages:
            if "cold" in message:
                key = "laugh"
                if is_not_recent(key, delay=1):
                    await context.bot.send_sticker(
                        chat_id=update.effective_chat.id,
                        sticker=random.choice(LAUGH_STICKERS)
                    )
                    last_sent[key] = datetime.now(timezone.utc)
                break
    elif "pointu" in text or "sowwie" in text:
        key = "pointu"
        if is_not_recent(key):
            await context.bot.send_sticker(
                chat_id=update.effective_chat.id,
                sticker=random.choice(POINTU_STICKERS)
            )
            last_sent[key] = datetime.now(timezone.utc)
    elif "remember this" in text:
        key = "remember"
        if is_not_recent(key):
            await context.bot.send_sticker(
                chat_id=update.effective_chat.id,
                sticker=random.choice(REMEMBER_STICKERS)
            )
            last_sent[key] = datetime.now(timezone.utc)
    elif "okie" in text or text == "keyi":
        key = "okie"
        if is_not_recent(key):
            await context.bot.send_sticker(
                chat_id=update.effective_chat.id,
                sticker=random.choice(OKIE_STIKCERS)
            )
            last_sent[key] = datetime.now(timezone.utc)
            
    recent_messages.append(text)

async def add_attempt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    
    args = context.args
    try:
        user_name = args[0]
        logic.add_attempt(user_name)
    except Exception as e:
        await update.message.reply_text(f'{e}')
        return
    
    await update.message.reply_text(f"Added 1 attempt for {user.name}")

async def get_user_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logic.reset_user_attempts()
    balance, attempts = logic.get_user_balance(update.effective_user.id)
    escaped_name = html.escape(update.effective_user.name)
    response = (
        f"👤 <b>{escaped_name}</b>\n"
        f"💰 <b>Balance:</b> {balance}\n"
        f"🎯 <b>Tries left:</b> {attempts}"
    )
    await update.message.reply_text(response, parse_mode="HTML")

async def generate_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    top_users, top_withdrawals = logic.generate_leaderboard()
    
    num_width_users = len(str(len(top_users)))
    num_width_withdrawals = len(str(len(top_withdrawals)))
    
    all_entries = top_users + top_withdrawals
    max_name_len = max(len(entry.get("user_name", "")) for entry in all_entries) if all_entries else 0
    
    # Calculate max amount widths
    max_balance_width = max(len(str(user.get("balance", 0))) for user in top_users) if top_users else 1
    max_withdrawal_width = max(len(str(entry.get("amount", 0))) for entry in top_withdrawals) if top_withdrawals else 1
    
    lines = ["🏆 <b>Leaderboard</b> 🏆"]
    
    # --- Top Balances ---
    if top_users:
        lines.append("\n💰 <b>Top Balances</b>")
        for i, user in enumerate(top_users, start=1):
            name = html.escape(user.get("user_name", "Unknown"))
            balance = user.get("balance", 0)
            
            if i <= 3:
                medal = ["🥇", "🥈", "🥉"][i-1]
            else:
                medal = f"{i:>{num_width_users}}."
            
            lines.append(f"{medal} {name:<{max_name_len}} {balance:>{max_balance_width}}")
    else:
        lines.append("No users found.")
    
    # --- Top Withdrawals ---
    if top_withdrawals:
        lines.append("\n💸 <b>Top Withdrawals</b>")
        for i, entry in enumerate(top_withdrawals, start=1):
            name = html.escape(entry.get("user_name", "Unknown"))
            amount = entry.get("amount", 0)
            timestamp = entry.get("timestamp")
            ago = html.escape(time_ago(timestamp) if timestamp else "Unknown time")
            
            if i <= 3:
                medal = ["🥇", "🥈", "🥉"][i-1]
            else:
                medal = f"{i:>{num_width_withdrawals}}."
            
            lines.append(f"{medal} {name:<{max_name_len}} {amount:>{max_withdrawal_width}} ({ago})")
    else:
        lines.append("No withdrawals found.")
    
    response = "\n".join(lines)
    await update.message.reply_text(response, parse_mode="HTML")

async def get_user_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    attempt_list = logic.get_user_history(update.effective_user.id)
    if not attempt_list:
        escaped_name = html.escape(update.effective_user.name)
        await update.message.reply_text(f"No history found for {escaped_name}", parse_mode="HTML")
        return
    
    # Calculate the maximum amount width for alignment
    max_amount_width = max(len(str(entry.get("amount", 0))) for entry in attempt_list)
    
    escaped_name = html.escape(update.effective_user.name)
    response = f"📜 History for <b>{escaped_name}</b>\n\n"
    
    for attempt in attempt_list:
        line = format_history_entry(attempt, max_amount_width)
        response += f"<code>{line}</code>\n"
    
    await update.message.reply_text(response, parse_mode="HTML")

async def get_bank_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logic.top_up_bank()
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    balance = logic.get_bank_balance()
    await update.message.reply_text(f'Bank has {balance}')    
    
async def set_user_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    
    args = context.args
    try:
        user_name = args[0]
        amount = int(args[1])
        logic.set_user_balance(user_name, amount)
        await update.message.reply_text(f"User {user.name}'s balance set to {amount}")
    except Exception:
        await update.message.reply_text("Invalid format")

async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        sticker_id = update.message.sticker.file_id
        # print(sticker_id)
        now = datetime.now(timezone.utc)
        sticker_group = None
        if sticker_id in SLEEP_STICKERS:
            key = "sleep"
            if is_not_recent(key):
                await context.bot.send_sticker(
                chat_id=update.effective_chat.id,
                sticker=CHICK_TUCKU
            )
            last_sent[key] = now

        if sticker_id in LOOKIE_STICKERS:
            sticker_group = "lookie_stickers"
        elif sticker_id in GOOD_STICKERS:
            sticker_group = "good_stickers"
        elif sticker_id in ANGRY_STICKERS:
            sticker_group = "angry_stickers"

        if sticker_group:
            if recent_stickers[sticker_group]["last_sent"] + timedelta(minutes=1) < now:
                recent_stickers[sticker_group]["combo"] = 1
                recent_stickers[sticker_group]["last_sent"] = now
                return
            combo = recent_stickers[sticker_group]["combo"]
            chance = convert_combo_to_chance(combo)
            if roll_chance(chance):
                await context.bot.send_sticker(
                chat_id=update.effective_chat.id,
                sticker=sticker_id
            )
                recent_stickers[sticker_group]["combo"] = 0
                recent_stickers[sticker_group]["last_sent"] = now
            else:
                recent_stickers[sticker_group]["combo"] += 1
                recent_stickers[sticker_group]["last_sent"] = now

    except Exception as e:
        print(e)
    
def convert_combo_to_chance(combo: int) -> int:
    # The return values represent chance in %
    if combo < 1:
        return 0
    elif combo == 1:
        return 20
    elif combo == 2:
        return 25
    elif combo == 3:
        return 33
    else:
        return 50
    
def time_ago(timestamp: datetime) -> str:
    now = datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    diff = now - timestamp

    minutes = diff.total_seconds() // 60
    hours = diff.total_seconds() // 3600
    days = diff.total_seconds() // 86400

    if minutes < 1:
        return "Just now"
    elif minutes < 60:
        return f"{int(minutes)} minute{'s' if minutes != 1 else ''} ago"
    elif hours < 24:
        return f"{int(hours)} hour{'s' if hours != 1 else ''} ago"
    else:
        return f"{int(days)} day{'s' if days != 1 else ''} ago"

def format_history_entry(entry, max_amount_width):
    """Format a single history record into readable text."""
    timestamp = entry.get("timestamp")

    ago = time_ago(timestamp)
    amount = entry.get("amount", 0)
    success = entry.get("is_successful", False)

    status_emoji = "✅" if success else "❌"
    return f"{status_emoji} | {amount:>{max_amount_width}} | {ago}"

def roll_chance(chance: int) -> bool:
    return chance >= random.randint(1, 100)