import asyncio
import html
import random
from datetime import datetime, timezone, timedelta
import database.button_db as database
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

keyboard = [
    [InlineKeyboardButton("Hit!", callback_data="hit_button")]
]

async def hit_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User pressed inline button."""
    query = update.callback_query
    user = query.from_user
    user_id = user.id

    game = get_or_create_game(user_id, user.name)

    score = game["score"]

    if is_add_score_success(score):
        game["score"] += 1
        game["timestamp"] = datetime.now(timezone.utc)

        text = f"⭐ Score: {game['score']}"
    else:
        game["in_progress"] = False
        text = f"💥 Poof at score {score}!\nHit the button to go again."
    
    database.log_button_game(game)

    await update.callback_query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await update.callback_query.answer()

async def summon_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User typed /button (start or continue game)."""
    user = update.effective_user
    user_id = user.id
    user_name = user.name

    game = get_or_create_game(user_id, user_name)
    database.log_button_game(game)

    text = f"⭐ Score: {game['score']}"

    await update.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
def get_or_create_game(user_id: int, user_name: str):
    game = database.get_button_game(user_id)
    if game is None:
        game = {
            "user_id": user_id,
            "user_name": user_name,
            "score": 0,
            "timestamp": datetime.now(timezone.utc),
            "in_progress": True
        }
    
    return game

def is_add_score_success(score) -> bool:
    return random.randint(1, 100) >= score

async def get_highscores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    all_time, weekly = database.get_button_highscores()
    
    lines = ["🏆 <b>Leaderboard</b> 🏆", "", "<b>All-time highscores</b>"]
    
    # All-time highscores
    for count, user_data in enumerate(all_time, start=1):
        user_name = html.escape(user_data.get("user_name", "Unknown"))
        score = user_data.get("score", 0)
        lines.append(f"{count}. {user_name} - {score}")
    
    lines.append("")
    lines.append("<b>Weekly highscores</b>")
    
    # Weekly highscores
    for count, user_data in enumerate(weekly, start=1):
        user_name = html.escape(user_data.get("user_name", "Unknown"))
        score = user_data.get("score", 0)
        lines.append(f"{count}. {user_name} - {score}")
    
    message = "\n".join(lines)
    await update.message.reply_text(message, parse_mode="HTML")

async def weekly_reset_loop():
    while True:
        now = datetime.now(timezone.utc)

        # Calculate next Saturday 12:00 UTC
        days_until_saturday = (5 - now.weekday()) % 7  # Saturday = 5
        next_reset = (now + timedelta(days=days_until_saturday)).replace(
            hour=12, minute=0, second=0, microsecond=0
        )

        # If we are already past today 12:00 UTC, add 7 days
        if next_reset <= now:
            next_reset += timedelta(days=7)

        # Time to sleep until next reset
        sleep_seconds = (next_reset - now).total_seconds()
        print(f"[Weekly Reset] Sleeping for {sleep_seconds} seconds until next reset...")
        await asyncio.sleep(sleep_seconds)

        # Perform reset
        await database.reset_weekly_button_games()
