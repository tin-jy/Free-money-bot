from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime, timedelta, timezone
from collections import deque
import logic
from constants import *
import random

pending_takes = {}
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
        sticker=random.choice(BAD_STICKERES),
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
        if random.randint(1, 4) == 1:
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
    pending_takes[user.id] = True

def is_not_recent(key, delay=5):
    return key not in last_sent or last_sent[key] + timedelta(minutes=delay) < datetime.now(timezone.utc)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text

    if user.id in pending_takes:   
        try:
            amount = int(text)
        except ValueError:
            del pending_takes[user.id]
            return
        del pending_takes[user.id]
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
    elif "have no proo" in text:
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
    elif text.startswith("i'm ") or text.startswith("im "):
        if random.randint(1, 10) == 1:
            remaining = " ".join(text.split()[1:])
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
    elif "pointu" in text:
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

    recent_messages.append(text)

async def add_attempt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("Admin only")
        return
    
    args = context.args
    try:
        user_name = args[0]
        logic.add_attempt(user_name)
    except Exception as e:
        await update.message.reply_text(f'{e}')
        return
    
    await update.message.reply_text(f"Added 1 attempt for {user.name}")

async def get_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logic.reset_user_attempts()
    balance, attempts = logic.get_balance(update.effective_user.id)
    response = (
        f"👤 *{update.effective_user.name}*\n"
        f"💰 *Balance:* {balance}\n"
        f"🎯 *Tries left:* {attempts}"
    )

    await update.message.reply_text(response, parse_mode="Markdown")

async def generate_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    response = logic.generate_leaderboard()
    await update.message.reply_text(response, parse_mode="Markdown")

async def get_bank_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logic.top_up_bank()
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("Admin only")
    
    balance = logic.get_bank_balance()
    await update.message.reply_text(f'Bank has {balance}')    
    
async def set_user_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("Admin only")
    
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
            print(chance)
            if chance >= random.randint(1, 100):
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