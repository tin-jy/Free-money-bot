from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone
from pymongo import ASCENDING, DESCENDING
import os
import random
from constants.constants import *

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["Geiqianbot"]
bank_collection = db["bank"]
users_collection = db["users"]
logs_collection = db["logs"]
drop_ball_collection = db["dropball"]
button_game_collection = db["button_game"]

def get_bank_balance() -> int:
    record = bank_collection.find_one()
    assert record

    return record.get("balance", 0)

def get_bank_next_top_up() -> datetime:
    record = bank_collection.find_one()
    assert record

    return record.get("next_top_up", None)

def decrement_bank_balance(amount: int) -> bool:
    result = bank_collection.update_one(
        {},
        {"$inc": {"balance": amount * -1}}
    )
    return result

def increment_bank_balance(amount: int) -> bool:
    result = bank_collection.update_one(
        {},
        {"$inc": {"balance": amount}}
    )
    return result

def increment_lifetime_total(amount: int) -> bool:
    result = bank_collection.update_one(
        {},
        {"$inc": {"lifetime_total": amount}}
    )
    return result

def get_user_balance(user_id: int):
    user = users_collection.find_one({"user_id": user_id})

    if user:
        return user.get("balance", 0)
    else:
        return -1

def get_remaining_attempts(user_id: int) -> int:
    user = users_collection.find_one({"user_id": user_id})

    if user:
        return user.get("attempts", 0)
    else:
        return -1

def decrement_remaining_attempts(user_id: int):
    result = users_collection.update_one(
        {"user_id": user_id},
        {"$inc": {"attempts": -1}}
    )
    return result

def decrement_user_balance(user_id: int, amount):
    result = users_collection.update_one(
        {"user_id": user_id},
        {"$inc": {"balance": amount * -1}}
    )
    return result

def increment_user_balance(user_id: int, amount):
    result = users_collection.update_one(
        {"user_id": user_id},
        {"$inc": {"balance": amount}}
    )
    return result

def create_user_if_not_exist(user_id: int, user_name: str) -> bool:
    """
    Creates a new user in the 'users' collection if one does not already exist.
    Each user has: user_id, user_name, balance, and attempts.
    """
    existing_user = users_collection.find_one({"user_id": user_id})
    
    if not existing_user:
        user_doc = {
            "user_id": user_id,
            "user_name": user_name,
            "balance": 0,
            "attempts": STARTING_ATTEMPTS
        }
        users_collection.insert_one(user_doc)
        return True
    
    print(f"ℹ️ User {user_name} ({user_id}) already exists.")
    return False

def add_attempt(user_name):
    result = users_collection.update_one(
        {"user_name": user_name},
        {"$inc": {"attempts": 1}}
    )
    return result

def rank_users(top_n: int = 10):
    top_users = list(
        users_collection.find({}, {"_id": 0, "user_name": 1, "balance": 1})
        .sort("balance", -1)
        .limit(top_n)
    )
    return top_users

def rank_withdrawals(top_n: int = 10):
    # Only successful withdrawals
    top_withdrawals = list(
        logs_collection.find(
            {"is_successful": True},
            {"_id": 0, "user_name": 1, "amount": 1, "timestamp": 1}
        )
        .sort("amount", -1)
        .limit(top_n)
    )
    return top_withdrawals

def get_withdrawal_history(last_n: int = 10):
    recent_withdrawals = list(
        logs_collection.find(
            {"reason": {"$ne": "No attempts"}},
            {"_id": 0, "user_name": 1, "amount": 1, "timestamp": 1, "is_successful": 1, "reason": 1}
        )
        .sort("timestamp", -1)  # newest first
        .limit(last_n)
    )
    return recent_withdrawals

def top_up_bank():
    """
    Perform missed daily top-ups at 12:00 UTC.
    Only top-ups that are due will be applied.
    Returns total top-up amount.
    """
    bank = bank_collection.find_one()
    assert bank

    last_update: datetime = bank.get("last_update", datetime.now(timezone.utc))
    now = datetime.now(timezone.utc)

    # Make last_update timezone-aware
    if last_update.tzinfo is None:
        last_update = last_update.replace(tzinfo=timezone.utc)

    while last_update + timedelta(days=1) <= now:
        amount = random.expovariate(1 / MEAN_DAILY_TOP_UP)
        # To ensure min 1, max 150
        amount = max(min(int(round(amount)), DAILY_TOP_UP), 1)
        increment_bank_balance(amount)
        increment_lifetime_total(amount)
        last_update += timedelta(days=1)

    bank_collection.update_one({}, {"$set": {"last_update": last_update}})

def reset_user_attempts():
    bank = bank_collection.find_one()
    assert bank

    now = datetime.now(timezone.utc)
    last_reset = bank.get("last_weekly_reset")
    if last_reset.tzinfo is None:
        last_reset = last_reset.replace(tzinfo=timezone.utc)

    is_time_to_reset = False
    while last_reset + timedelta(days=7) <= now:
        is_time_to_reset = True
        last_reset += timedelta(days=7)

    if is_time_to_reset:
        users_collection.update_many({}, {"$set": {"attempts": STARTING_ATTEMPTS}})
        bank_collection.update_one({}, {"$set": {"last_weekly_reset": last_reset}})

def set_user_balance(user_name, amount):
    users_collection.update_one(
        {"user_name": user_name},
        {"$set": {"balance": amount}}
    )
    return amount

def log_take_attempt(user_id, user_name, chat_id, chat_type, amount, is_successful, reason):
    log_entry = {
        "user_id": user_id,
        "user_name": user_name,
        "chat_id": chat_id,
        "chat_type": chat_type,
        "amount": amount,
        "timestamp": datetime.now(timezone.utc),
        "is_successful": is_successful,
        "reason": reason
    }
    logs_collection.insert_one(log_entry)

def get_user_history(user_id, limit=10):
    cursor = logs_collection.find(
        {
            "user_id": user_id,
            "reason": {"$ne": "No attempts"}  # Exclude entries with this reason
        }
    ).sort("timestamp", -1).limit(limit)
    return list(cursor) or []

def generate_next_gamma(avg, shape=2.0):
    scale = avg / shape
    return random.gammavariate(shape, scale)

def top_up_bank_random():
    record = bank_collection.find_one({})
    assert record

    now = datetime.now(timezone.utc)
    next_top_up = record.get("next_top_up", now)
    if next_top_up.tzinfo is None:
        next_top_up = next_top_up.replace(tzinfo=timezone.utc)

    total_amount = 0
    while next_top_up < now:
        amount = random.expovariate(1 / MEAN_DAILY_TOP_UP) # 30
        amount = max(min(int(amount), DAILY_TOP_UP), 1) # 300
        total_amount += amount
        time_to_next_in_minutes = generate_next_gamma(avg=1440)
        next_top_up += timedelta(minutes=time_to_next_in_minutes)
    
    if total_amount:
        bank_collection.update_one({}, {
            "$set": {"next_top_up": next_top_up},
            "$inc": {"balance": total_amount}
        })

def insert_drop_ball_game(game):
    drop_ball_collection.insert_one(game)


def get_dropball_net_profit():
    collection = db["dropball"]

    pipeline = [
        {
            "$project": {
                "profit": {
                    "$multiply": [
                        "$multiplier",
                        { "$subtract": ["$num_of_balls", "$cashout_amount"] }
                    ]
                }
            }
        },
        {
            "$group": {
                "_id": None,
                "total_profit": { "$sum": "$profit" }
            }
        }
    ]

    result = list(collection.aggregate(pipeline))

    if result:
        return result[0]["total_profit"]
    else:
        return 0
    
def get_dropball_stats(user_id: int):
    pipeline = [
        {"$match": {"user_id": user_id}},
        {
            "$group": {
                "_id": None,
                "total_spent": {
                    "$sum": {"$multiply": ["$multiplier", "$num_of_balls"]}
                },
                "total_cashout": {"$sum": "$cashout_amount"},
                "count_total": {"$sum": 1},
                "count_cashout": {
                    "$sum": {
                        "$cond": [{"$gt": ["$cashout_amount", 0]}, 1, 0]
                    }
                },
            }
        }
    ]

    result = list(drop_ball_collection.aggregate(pipeline))

    if not result:
        return {
            "lifetime_spent": 0,
            "lifetime_cashout": 0,
            "lifetime_net": 0,
            "cashout_percentage": 0.0,
        }

    data = result[0]

    lifetime_spent = data["total_spent"]
    lifetime_cashout = data["total_cashout"]
    
    lifetime_net = lifetime_cashout - lifetime_spent

    if data["count_total"] > 0:
        cashout_percentage = data["count_cashout"] / data["count_total"]
    else:
        cashout_percentage = 0.0

    return {
        "lifetime_spent": lifetime_spent,
        "lifetime_cashout": lifetime_cashout,
        "lifetime_net": lifetime_net,
        "cashout_percentage": cashout_percentage,
    }