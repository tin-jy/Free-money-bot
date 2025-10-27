from telegram import Update
from telegram.ext import ContextTypes
import logic
from constants import *
import random

pending_takes = {}

async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'Hello {update.effective_user.first_name}')

async def bad(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    send_sticker = random.randint(0, 2)
    if send_sticker:
        await context.bot.send_sticker(
            chat_id=update.effective_chat.id,
            sticker=random.choice(BAD_STICKERES),
            reply_to_message_id=update.message.id
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=random.choice(BAD),
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
        await update.message.reply_text(USER_GREEDY)
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
        await update.message.reply_text(NO_MORE_ATTEMPTS_MESSAGE)
        return

    if args:
        try:
            amount = int(args[0])
        except ValueError:
            await update.message.reply_text(INVALID_VALUE_ERROR_MESSAGE)
            return
        take_status = logic.take(user.id, amount)
        await process_take_status(update, context, take_status, amount)
        return

    await update.message.reply_text(AMOUNT_QUERY)
    pending_takes[user.id] = True

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
        await process_take_status(update, context, take_status, amount)

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
        print(update.message.sticker.file_id)
    except Exception:
        pass
    
