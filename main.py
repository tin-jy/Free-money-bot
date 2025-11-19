from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram.error import Conflict
from dotenv import load_dotenv
from game_logic.drop_ball_game import *
import os
import time
import logging
import asyncio
from constants.constants import *

import game_logic.commands as commands
import game_logic.button as button
import admin.admin as admin

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

WHITELISTED_USER_IDS = {NUT, KAI, COLE, LAS, HONG, ELLE, YS}
WHITELISTED_CHAT_IDS = {CCOS}
ADMIN_IDS = {NUT}

def build_application():
    app = ApplicationBuilder().token(TOKEN).build()

    user_filter = filters.User(user_id=WHITELISTED_USER_IDS)
    admin_filter = filters.User(user_id=ADMIN_IDS)
    dm_filter = filters.ChatType.PRIVATE
    chat_filter = filters.Chat(chat_id=WHITELISTED_CHAT_IDS)

    # Regular commands
    app.add_handler(CommandHandler("help", commands.help))
    app.add_handler(CommandHandler("geiwoqian", commands.take, filters=user_filter))
    app.add_handler(CommandHandler("balance", commands.get_user_balance, filters=user_filter))
    app.add_handler(CommandHandler("leaderboard", commands.generate_leaderboard))
    app.add_handler(CommandHandler("history", commands.get_user_history, filters=user_filter))
    app.add_handler(CommandHandler("recent", commands.get_withdrawal_history))

    # Lucky9 game
    app.add_handler(CommandHandler("lucky9", start_or_find_game))
    app.add_handler(CallbackQueryHandler(start_drop, pattern="^start_drop$"))
    app.add_handler(CallbackQueryHandler(stop_drop, pattern="^stop_drop$"))
    app.add_handler(CallbackQueryHandler(random_drop, pattern="^random_drop$"))
    app.add_handler(CallbackQueryHandler(retry, pattern="^retry$"))
    app.add_handler(CallbackQueryHandler(cash_out, pattern="^cash_out$"))
    app.add_handler(CallbackQueryHandler(play_again, pattern="^play_again$"))

    # Button press game
    app.add_handler(CommandHandler("button", button.summon_button))
    app.add_handler(CommandHandler("buttonleaderboard", button.get_highscores))
    app.add_handler(CallbackQueryHandler(button.hit_button, pattern="^hit_button$"))

    # Hidden commands
    app.add_handler(CommandHandler("bad", commands.bad))
    app.add_handler(CommandHandler("badbot", commands.bad))
    app.add_handler(CommandHandler("good", commands.good))
    app.add_handler(CommandHandler("goodbot", commands.good))

    # Message handler
    app.add_handler(MessageHandler(filters.Sticker.ALL, commands.handle_sticker))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, commands.handle_message))

    # Admin commands
    app.add_handler(CommandHandler("hello", admin.hello, filters=admin_filter))
    app.add_handler(CommandHandler("addattempt", admin.add_attempt, filters=admin_filter))
    app.add_handler(CommandHandler("setbalance", admin.set_user_balance, filters=admin_filter))
    app.add_handler(CommandHandler("bank", admin.get_bank_balance, filters=admin_filter))
    app.add_handler(CommandHandler("announcement", admin.announcement, filters=admin_filter))

    async def error_handler(update, context):
        err = context.error
        if isinstance(err, Conflict):
            logger.info("Conflict detected: another bot instance is running. Ignored.")
        else:
            logger.error("Exception while handling an update:", exc_info=err)

    # Error handlers
    app.add_error_handler(error_handler)

    return app

def run_bot():
    while True:
        try:
            app = build_application()
            logger.info("Bot started.")
            # run_polling manages its own loop internally
            app.run_polling(stop_signals=None)
        except KeyboardInterrupt:
            logger.info("Bot stopped manually.")
            break
        except Exception as e:
            logger.error(f"Bot crashed with error: {e}", exc_info=True)
            logger.info("Restarting bot in 5 seconds...")
            time.sleep(5)


if __name__ == "__main__":
    asyncio.run(run_bot())
