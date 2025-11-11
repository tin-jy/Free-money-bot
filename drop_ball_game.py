import random
import math
from constants import COGRATULATIONS_STICKERS
from typing import List, Tuple
from datetime import datetime, timedelta, timezone
from database import increment_user_balance, decerement_user_balance, get_user_balance, insert_drop_ball_game, get_dropball_net_profit, get_dropball_stats
from telegram import Update
from telegram.ext import ContextTypes

games = []

NOT_ENOUGH_TO_START = -1
NOT_ENOUGH_TO_DROP = -2
NO_EXISTING_BALL_DROP_GAME = -3
GAME_ALREADY_EXISTS = -4
CANNOT_CASH_OUT = -5
UNPROFITABLE = -6
GAME_STARTED = 1
FIRST_DROP_SUCCESS = 2
SECOND_DROP_SUCCESS = 3
GAME_OVER = 4
CASH_OUT_SUCCESS = 5
JACKPOT = 6

JACKPOT_PRIZE = 1200

def create_game(user_id: int, user_name: str, multipler=1):
    net_profit = get_dropball_net_profit()
    if net_profit < -1000:
        return UNPROFITABLE
    for game in games:
        if game.get("user_id") == user_id:
            return GAME_ALREADY_EXISTS
    new_game = {
        "user_id": user_id,
        "user_name": user_name,
        "game_state": [False, False, False, False, False, False, False, False, False],
        "first_drop": None,
        "multiplier": multipler,
        "num_of_balls": 0
    }
    games.append(new_game)
    return GAME_STARTED

def execute_drop_ball(user_id: int):
    global games
    timestamp = datetime.now(timezone.utc)
    current_game = None
    for game in games:
        if game.get("user_id") == user_id:
            current_game = game
            break
    if not current_game:
        return NO_EXISTING_BALL_DROP_GAME, None
    
    first_drop = current_game.get("first_drop")
    multipler = current_game.get("multiplier")
    if not first_drop:
        if get_user_balance(user_id) < multipler:
            return NOT_ENOUGH_TO_DROP, None
        decerement_user_balance(user_id, amount=multipler)
        current_game["first_drop"] = timestamp
        return FIRST_DROP_SUCCESS, None
    
    timediff = timestamp - first_drop
    bin, pos = convert_time_diff_to_drop_position(timediff)
    game_state = current_game.get("game_state")
    data = {
        "bin": bin,
        "pos": pos,
        "timediff": timediff,
        "game_state": game_state
    }

    if game_state[bin]: # Ball hit occupied spot, game over
        game_data = {
            "user_id": current_game.get("user_id"),
            "user_name": current_game.get("user_name"),
            "multiplier": current_game.get("multiplier"),
            "num_of_balls": current_game.get("num_of_balls") + 1,
            "cashout_amount": 0
        }
        insert_drop_ball_game(game_data)
        games.remove(current_game)
        return GAME_OVER, data
    
    game_state[bin] = True
    current_game["first_drop"] = None
    current_game["num_of_balls"] += 1
    if current_game.get("num_of_balls") == 9:
        execute_cash_out(user_id)
        return JACKPOT, data
    return SECOND_DROP_SUCCESS, data

def execute_cash_out(user_id: int):
    global games
    current_game = None
    for game in games:
        if game.get("user_id") == user_id:
            current_game = game
            break
    if not current_game:
        return NO_EXISTING_BALL_DROP_GAME, 0
    
    game_state = current_game.get("game_state")
    max_streak = 0
    streak = 0
    for bin in game_state:
        if bin:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    if max_streak < 3:
        return CANNOT_CASH_OUT, 0
    cashout_amount = convert_streak_to_amount(max_streak)
    increment_user_balance(user_id, cashout_amount)
    game_data = {
        "user_id": current_game.get("user_id"),
        "user_name": current_game.get("user_name"),
        "multiplier": current_game.get("multiplier"),
        "num_of_balls": current_game.get("num_of_balls"),
        "cashout_amount": cashout_amount
    }
    insert_drop_ball_game(game_data)
    games.remove(current_game)
    return CASH_OUT_SUCCESS, cashout_amount

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

async def start_drop_ball(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_name = update.effective_user.name
    result = create_game(user_id, user_name)
    if result == UNPROFITABLE:
        update.message.reply_text("Game is suspended due to unexpected losses")
    if result == GAME_ALREADY_EXISTS:
        await update.message.reply_text("Game already exists. Use /drop to drop a ball")
        return
    await update.message.reply_text("Game started! Use /drop to drop a ball.")
    

async def drop_ball(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    status, data = execute_drop_ball(user_id)
    if status == NO_EXISTING_BALL_DROP_GAME:
        await update.message.reply_text("Use /startlucky9 to start a game first")
        return
    if status == NOT_ENOUGH_TO_DROP:
        await update.message.reply_text("You don't have enough credits")
        return
    if status == FIRST_DROP_SUCCESS:
        # await update.message.reply_text("Use /drop again to time your drop")
        return
    if status == GAME_OVER:
        assert data
        game_state = data.get("game_state")
        bin = data.get("bin")
        timediff = data.get("timediff")
        pos = data.get("pos")
        formatted_game_data = format_game_state(game_state, bin, True)
        message = f"<pre>GAME OVER\n\nTime: {round(timediff.total_seconds(), 3)}s\nAim: {round(pos + 5, 3)}\nHit: {bin + 1}\n\n{formatted_game_data}</pre>"
        await update.message.reply_text(message, parse_mode="HTML")
        await update.message.reply_text("/startlucky9 to play again")
        return
    if status == SECOND_DROP_SUCCESS:
        assert data
        game_state = data.get("game_state")
        bin = data.get("bin")
        timediff = data.get("timediff")
        pos = data.get("pos")
        formatted_game_data = format_game_state(game_state, bin, False)
        message = f"<pre>Time: {round(timediff.total_seconds(), 3)}s\nAim: {round(pos + 5, 3)}\nHit: {bin + 1}\n\n{formatted_game_data}</pre>"
        await update.message.reply_text(message, parse_mode="HTML")
        return
    if status == JACKPOT:
        assert data
        game_state = data.get("game_state")
        bin = data.get("bin")
        timediff = data.get("timediff")
        pos = data.get("pos")
        formatted_game_data = format_game_state(game_state, bin, False)
        message = f"<pre>JACKPOT!!!\n\nTime: {round(timediff.total_seconds(), 3)}s\nAim: {round(pos + 5, 3)}\nHit: {bin + 1}\n\n{formatted_game_data}</pre>"
        await update.message.reply_text(message, parse_mode="HTML")
        await context.bot.send_sticker(
            chat_id=update.effective_chat.id,
            sticker=random.choice(COGRATULATIONS_STICKERS),
            reply_to_message_id=update.message.id
        )
        await update.message.reply_text(f"CASHED OUT FOR {JACKPOT_PRIZE}!!!")
        return
    
async def cash_out(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    status, amount = execute_cash_out(user_id)
    if status == NO_EXISTING_BALL_DROP_GAME:
        await update.message.reply_text("No game in progress")
        return
    if status == CANNOT_CASH_OUT:
        await update.message.reply_text("You need a chain of at least 3 to cash out")
        return
    
    await update.message.reply_text(f"Cashed out for {amount} credits!")

async def help_aim(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with open("dropball chance distribution.png", "rb") as f:
        await update.message.reply_photo(photo=f)

async def db_rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = f"""
NOTICE: This game costs credits to play

/startlucky9 to start
/drop twice to drop a ball
/cashout to cashout
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

Details: Each dropped ball costs 1 credit. Time the interval between /drop commands to aim. After 1 second, the ball starts in the middle and swings left. Releasing before 1s or after 17s will cause the ball to randomly fire. The ball completes 1 oscillation every 8 seconds.
    """
    await update.message.reply_text(message)

async def db_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    profit = get_dropball_net_profit()
    await update.message.reply_text(f"Net profit: {profit}")

async def lucky9_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    stats = get_dropball_stats(user_id)
    message = f"""
Balls dropped: {stats.get("lifetime_spent")}
Lifetime cashout: {stats.get("lifetime_cashout")}
Lifetime net: {stats.get("lifetime_net")}
Cashout percentage: {round(stats.get("cashout_percentage") * 100, 2)}%
"""
    await update.message.reply_text(message)


def format_game_state(game_state, latest_bin, game_over: bool):
    formatted_string = ""
    if game_over:
        for i in range(9):
            if i == latest_bin:
                formatted_string += "x "
            else:
                formatted_string += "  "
        formatted_string += "\n"
    for i in range(9):
        bin = game_state[i]
        if i == latest_bin:
            if game_over:
                formatted_string += "o "
            else:
                formatted_string += "x "
        elif bin:
            formatted_string += "o "
        else:
            formatted_string += "_ "
    formatted_string += "\n1 2 3 4 5 6 7 8 9"
    return formatted_string

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


# For testing
# t = 3
# idx, probs = sample_bin_at_time(t - 1, sigma=1.2, kernel="laplace")
# pointer_pos = round(pointer_position(t - 1), 2)
# print("t=", t, "pointer approx=", round(pointer_position(t - 1),2))
# print("probs:", ["{:.4f}".format(p) for p in probs])
# print("sampled bin:", idx)
# print()