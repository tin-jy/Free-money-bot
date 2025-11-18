import random
import math
from constants.constants import COGRATULATIONS_STICKERS
import database.lucky9_db as database
from database.database import decrement_user_balance, increment_user_balance, get_user_balance
from typing import List, Tuple
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import ContextTypes

GAME_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("START", callback_data="start_drop"),
        InlineKeyboardButton("STOP", callback_data="stop_drop")
    ],
    [
        InlineKeyboardButton("RANDOM", callback_data="random_drop"),
        InlineKeyboardButton("RETRY", callback_data="retry")
    ],
    [
        InlineKeyboardButton("CASH OUT 💰", callback_data="cash_out"),
        InlineKeyboardButton("AGAIN", callback_data="play_again")
    ]
])

MAX_BALLS = 9

EMPTY = 0
BALL = 1
PREV = 2
DEAD = -1

def is_live_game_exist(user_id: int) -> bool:
    game = database.get_live_game(user_id)
    if game:
        return True
    return False

def get_or_create_game(user_id: int, user_name: str) -> dict:
    game = database.get_live_game(user_id)
    if game is None:
        game = {
            "user_id": user_id,
            "user_name": user_name,
            "multiplier": 1,
            "first_drop": None,
            "num_of_balls": 0,
            "cashout_amount": 0,
            "gamestate": [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY],
            "in_progress": True
        }
        database.update_game(game)

    return game

def simulate_drop(game: dict, now: datetime=None) -> str:
    user_id = game.get("user_id")

    if get_user_balance(user_id) < game.get("multiplier"):
        return None
    decrement_user_balance(user_id, amount=game.get("multiplier"))
    
    if now is None:
        timediff = timedelta(seconds=0)
    else:
        first_drop: datetime = game.get("first_drop")
        if first_drop.tzinfo is None:
            first_drop = first_drop.replace(tzinfo=timezone.utc)
        timediff = now - first_drop
    bin, pos = convert_time_diff_to_drop_position(timediff)
    print(f"Bin: {bin}\nPos: {pos}")
    game["first_drop"] = None

    # Game over
    if game.get("gamestate")[bin] == BALL or game.get("gamestate")[bin] == PREV:
        game["in_progress"] = False

    game["gamestate"] = update_game_state(game.get("gamestate"), bin)
    game["num_of_balls"] += 1

    # If jackpot, automatic cashout
    if game.get("num_of_balls") == MAX_BALLS:
        cashout_amount = execute_cashout(game)
        return f"JACKPOT!!! Cashed out for {cashout_amount}!!!"

    database.update_game(game)

    if game["in_progress"]:
        new_text = "Keep going!\n\n"
    else:
        new_text = "GAME OVER :(\n\n"

    new_text += f"Time: {round(timediff.total_seconds(), 3)}\nAim: {round(pos + 5, 2)}\nHit: {bin + 1}\n\n"
    formatted_game_state = format_game_state(game.get("gamestate"))
    new_text += formatted_game_state
    
    return new_text

def execute_cashout(game: dict) -> int:
    max_streak = count_max_streak(game.get("gamestate"))
    cashout_amount = convert_streak_to_amount(max_streak)
    
    # Cashout successful
    if cashout_amount:
        game["in_progress"] = False
        game["cashout_amount"] = cashout_amount

        increment_user_balance(user_id=game.get("user_id"), amount=cashout_amount)
        database.update_game(game)
    
    return cashout_amount

async def start_or_find_game(update: Update, context = ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.name
    game = get_or_create_game(user_id, user_name)

    formatted_game_state = format_game_state(game.get("gamestate"))
    
    await update.message.reply_text(
        text=f"<pre>Hit the buttons to start!\n\n{formatted_game_state}</pre>",
        reply_markup=GAME_KEYBOARD,
        parse_mode="HTML"
    )

async def start_drop(update: Update, context = ContextTypes.DEFAULT_TYPE):
    now = datetime.now(timezone.utc)

    query = update.callback_query
    user_id = update.effective_user.id
    user_name = update.effective_user.name
    game = get_or_create_game(user_id, user_name)
    game["first_drop"] = now
    database.update_game(game)

    await query.answer("Started!", show_alert=False)

async def stop_drop(update: Update, context = ContextTypes.DEFAULT_TYPE):
    now = datetime.now(timezone.utc)

    query = update.callback_query
    user_id = update.effective_user.id
    user_name = update.effective_user.name
    game = get_or_create_game(user_id, user_name)

    # User has not hit START
    if game.get("first_drop") is None:
        await query.answer("Hit START first", show_alert=False)
        return

    new_text = simulate_drop(game, now)
    # Not enough credits
    if new_text is None:
        await query.answer("Not enough credits", show_alert=False)
        return
    
    await query.edit_message_text(
        text=f"<pre>{new_text}</pre>",
        reply_markup=GAME_KEYBOARD,
        parse_mode="HTML"
    )

async def random_drop(update: Update, context = ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    user_name = update.effective_user.name
    game = get_or_create_game(user_id, user_name)

    new_text = simulate_drop(game)
    # Not enough credits
    if new_text is None:
        await query.answer("Not enough credits.", show_alert=False)
        return

    await query.edit_message_text(
        text=f"<pre>{new_text}</pre>",
        reply_markup=GAME_KEYBOARD,
        parse_mode="HTML"
    )

async def retry(update: Update, context = ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    user_name = update.effective_user.name
    game = get_or_create_game(user_id, user_name)

    game["first_drop"] = None
    database.update_game(game)
    await query.answer("Reset successfully!", show_alert=False)

async def cash_out(update: Update, context = ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    user_name = update.effective_user.name
    game = get_or_create_game(user_id, user_name)

    cashout_amount = execute_cashout(game)
    if cashout_amount:
        new_text = f"Cashed out for {cashout_amount} credits!"
        await query.edit_message_text(
            text=f"<pre>{new_text}</pre>",
            reply_markup=GAME_KEYBOARD,
            parse_mode="HTML"
        )
    else:
        await query.answer("Cannot cash out!", show_alert=False)

async def play_again(update: Update, context = ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    user_name = update.effective_user.name
    
    if is_live_game_exist(user_id):
        await query.answer("Finish current game first!", show_alert=False)
        return
    
    game = get_or_create_game(user_id, user_name)
    formatted_game_state = format_game_state(game.get("gamestate"))
    await query.edit_message_text(
        text=f"<pre>Hit the buttons to start!\n\n{formatted_game_state}</pre>",
        reply_markup=GAME_KEYBOARD,
        parse_mode="HTML"
    )

def convert_streak_to_amount(streak: int) -> int:
    if streak == 3:
        return 6
    if streak == 4:
        return 12
    if streak == 5:
        return 24
    if streak == 6:
        return 60
    if streak == 7:
        return 150
    if streak == 8:
        return 400
    if streak == 9:
        return 1200
    
    return 0
    
def convert_time_diff_to_drop_position(timediff: timedelta) -> Tuple[int, float]:
    t = float(timediff.total_seconds())
    MIN_TIME = 1
    MAX_TIME = 17

    # If user is too fast or too slow, randomly launch ball
    if t < MIN_TIME or t > MAX_TIME:
        t = random.uniform(MIN_TIME, MAX_TIME)

    # Adjusted time handled in pointer_position already
    pointer_pos = pointer_position(t)  # full precision for sampling
    idx, probs = sample_bin_at_time(t, sigma=1.2, kernel="laplace")

    pointer_pos_rounded = round(pointer_pos, 2)  # for display

    return idx, pointer_pos_rounded

def pointer_position(t: float, bins: int = 9) -> float:
    amplitude = (bins - 1) / 2.0
    omega = -math.pi / 4
    adjusted_t = t - 1
    x = amplitude * math.sin(omega * adjusted_t)
    return x

def get_bin_positions(bins: int = 9) -> List[float]:
    mid = (bins - 1) / 2.0
    return [i - mid for i in range(bins)]

def gaussian_weights(x: float, bin_positions: List[float], sigma: float) -> List[float]:
    """Return unnormalized Gaussian weights for each bin given pointer x and sigma."""
    if sigma <= 0:
        raise ValueError("sigma must be > 0")
    two_sig_sq = 2.0 * sigma * sigma
    return [math.exp(- ((b - x) ** 2) / two_sig_sq) for b in bin_positions]

def laplace_weights(x: float, bin_positions: List[float], beta: float) -> List[float]:
    """Return unnormalized Laplace (double-exponential) weights for heavier tails."""
    if beta <= 0:
        raise ValueError("beta must be > 0")
    return [math.exp(- abs(b - x) / beta) for b in bin_positions]

def normalize(weights: List[float]) -> List[float]:
    s = sum(weights)
    if s == 0:
        n = len(weights)
        return [1.0 / n] * n
    return [w / s for w in weights]

def get_bin_probabilities(
    t: float,
    bins: int = 9,
    sigma: float = 1.0,
    kernel: str = "gaussian",
) -> List[float]:
    x = pointer_position(t, bins)
    bin_positions = get_bin_positions(bins)
    
    if kernel == "gaussian":
        weights = gaussian_weights(x, bin_positions, sigma)
    elif kernel == "laplace":
        weights = laplace_weights(x, bin_positions, sigma)
    else:
        raise ValueError("unknown kernel")
    
    return normalize(weights)

def sample_bin_at_time(
    t: float,
    bins: int = 9,
    sigma: float = 1.0,
    kernel: str = "gaussian",
    rng=random.random,
) -> Tuple[int, List[float]]:
    probs = get_bin_probabilities(t, bins=bins, sigma=sigma, kernel=kernel)
    r = rng()
    cum = 0.0
    for i, p in enumerate(probs):
        cum += p
        if r < cum:
            return i, probs
    return len(probs) - 1, probs

async def help_aim(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with open("dropball chance distribution.png", "rb") as f:
        await update.message.reply_photo(photo=f)

async def db_rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = f"""
NOTICE: This game costs credits to play

/startlucky9 to start
/helpaim for aim guidance
/lucky9stats for statistics

Payouts:
3 in a row | 6
4 in a row | 12
5 in a row | 24
6 in a row | 60
7 in a row | 150
8 in a row | 400
9 in a row | 1200

Details: Each dropped ball costs 1 credit. Time the interval between button presses to aim. After 1 second, the ball starts in the middle and swings left. Releasing before 1s or after 17s will cause the ball to randomly fire. The ball completes 1 oscillation every 8 seconds.
    """
    await update.message.reply_text(message)

# async def db_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     profit = get_dropball_net_profit()
#     await update.message.reply_text(f"Net profit: {profit}")

# async def lucky9_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     user_id = update.effective_user.id
#     stats = get_dropball_stats(user_id)
#     message = f"""
# Balls dropped: {stats.get("lifetime_spent")}
# Lifetime cashout: {stats.get("lifetime_cashout")}
# Lifetime net: {stats.get("lifetime_net")}
# Cashout percentage: {round(stats.get("cashout_percentage") * 100, 2)}%
# """
#     await update.message.reply_text(message)

def format_game_state(game_state: List) -> str:
    line1 = "" # Top row
    line2 = "" # Bottom row
    line3 = "1 2 3 4 5 6 7 8 9"

    for bin in game_state:
        if bin == DEAD:
            line1 += "x "
            line2 += "o "
        elif bin == BALL:
            line1 += "  "
            line2 += "o "
        elif bin == PREV:
            line1 += "  "
            line2 += "x "
        else: # bin == EMPTY
            line1 += "  "
            line2 += "_ "
    
    return f"{line1}\n{line2}\n{line3}"
    
def execute_help_aim(target_bin: float):
    if target_bin < 1 or target_bin > 9:
        return None
    target_bin -= 5
    t1 = 1 - 4 / math.pi * math.asin(target_bin / 4)
    t2 = 4 / math.pi * math.asin(target_bin / 4) - 3
    output = []
    while t1 < 17: 
        if t1 > 1:
            output.append(t1)
        t1 += 8
    while t2 < 17:
        if t2 > 1:
            if t2 not in output:
                output.append(t2)
        t2 += 8

    output.sort()
    return output

def update_game_state(game_state: List, new_bin_no: int) -> dict:
    for bin_no in range(9):
        if game_state[bin_no] == PREV:
            game_state[bin_no] = BALL
        if new_bin_no == bin_no:
            if game_state[bin_no] == EMPTY:
                game_state[bin_no] = PREV
            else: # Was BALL
                game_state[bin_no] = DEAD

    return game_state

def count_max_streak(game_state: List) -> int:
    max_streak = 0
    streak = 0
    for bin in game_state:
        if bin == BALL or bin == PREV:
            streak += 1
            max_streak = max(streak, max_streak)
        else:
            streak = 0
    return max_streak