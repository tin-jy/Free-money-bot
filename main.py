from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv
from commands import *
import os

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

app = ApplicationBuilder().token(TOKEN).build()

# Regular commands
app.add_handler(CommandHandler("hello", hello))
app.add_handler(CommandHandler("geiwoqian", take))
app.add_handler(CommandHandler("balance", get_balance))
app.add_handler(CommandHandler("bad", bad))
app.add_handler(CommandHandler("leaderboard", generate_leaderboard))

# Message handler
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Admin commands
app.add_handler(CommandHandler("add", add_attempt))
app.add_handler(CommandHandler("bank", get_bank_balance))

app.run_polling()