from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime, timedelta, timezone
from collections import deque
import game_logic.logic as logic
import html
from constants.constants import *
import random
import asyncio
from collections import defaultdict

async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id:
        user_id = update.effective_user.id
    else:
        user_id = "NA"
    if update.effective_chat.id:
        chat_id = update.effective_chat.id
    else:
        chat_id = "NA"
    await update.message.reply_text(f'Hello {update.effective_user.first_name}\nUser_id: {user_id}\nChat_id: {chat_id}')

async def announcement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = " ".join(context.args)

    if not message:
        await update.message.reply_text(
            "Please provide a message.\n\nUsage:\n/announcement <your message>"
        )
        return

    await context.bot.send_message(chat_id=CCOS, text=message)
    await update.message.reply_text("Announcement sent!")

async def add_attempt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user  
    args = context.args
    try:
        user_name = args[0]
        logic.add_attempt(user_name)
    except Exception as e:
        await update.message.reply_text(f'{e}')
        return
    
    await update.message.reply_text(f"Added 1 attempt for {user.name}")

async def get_bank_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logic.top_up_bank()
    balance = logic.get_bank_balance()
    next_top_up = logic.get_bank_next_top_up()
    assert isinstance(next_top_up, datetime)

    if next_top_up.tzinfo is None:
        next_top_up = next_top_up.replace(tzinfo=timezone.utc)

    line = time_till(next_top_up)

    await update.message.reply_text(f'Bank balance: {balance}\nTime to next top-up: {line}') 

async def set_user_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    args = context.args
    try:
        user_name = args[0]
        amount = int(args[1])
        logic.set_user_balance(user_name, amount)
        await update.message.reply_text(f"User {user_name}'s balance set to {amount}")
    except Exception:
        await update.message.reply_text("Invalid format")

def time_till(timestamp: datetime) -> str:
    now = datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    diff = timestamp - now

    minutes = diff.total_seconds() // 60
    hours = diff.total_seconds() // 3600

    if minutes < 1:
        return "Now"
    elif minutes < 60:
        return f"{int(minutes)} minute{'s' if minutes != 1 else ''}"
    else:
        return f"{int(hours)} hour{'s' if hours != 1 else ''}"