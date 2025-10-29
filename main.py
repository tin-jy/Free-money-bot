from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from telegram.error import Conflict
from dotenv import load_dotenv
from commands import *
import os
import time
import logging
import asyncio
from constants import *

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

WHITELISTED_USER_IDS = {NUT, KAI, COLE, LAS, HONG, ELLE}
ADMIN_IDS = {NUT}

# class WhitelistFilter(filters.UpdateFilter):
#     def filter(self, update: Update) -> bool:
#         user = update.effective_user
#         return user and user.id in WHITELISTED_USER_IDS


def build_application():
    app = ApplicationBuilder().token(TOKEN).build()

    whitelist_filter = filters.User(user_id=WHITELISTED_USER_IDS)
    admin_filter = filters.User(user_id=ADMIN_IDS)

    # Regular commands
    app.add_handler(CommandHandler("hello", hello))
    app.add_handler(CommandHandler("help", help))
    app.add_handler(CommandHandler("geiwoqian", take, filters=whitelist_filter))
    app.add_handler(CommandHandler("balance", get_user_balance, filters=whitelist_filter))
    app.add_handler(CommandHandler("leaderboard", generate_leaderboard, filters=whitelist_filter))
    app.add_handler(CommandHandler("history", get_user_history, filters=whitelist_filter))

    # Hidden commands
    app.add_handler(CommandHandler("bad", bad))
    app.add_handler(CommandHandler("badbot", bad))
    app.add_handler(CommandHandler("good", good))
    app.add_handler(CommandHandler("goodbot", good))

    # Message handler
    app.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Admin commands
    app.add_handler(CommandHandler("addattempt", add_attempt, filters=admin_filter))
    app.add_handler(CommandHandler("setbalance", set_user_balance, filters=admin_filter))
    app.add_handler(CommandHandler("bank", get_bank_balance, filters=admin_filter))

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
