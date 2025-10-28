from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone
import os
import random
from constants import *

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["Geiqianbot"]
bank_collection = db["bank"]
users_collection = db["users"]
logs_collection = db["logs"]

def get_bank_balance() -> int:
    record = bank_collection.find_one()
    if record:
        balance = record.get("balance", 0)
        return balance
    return -1

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
        amount = max(min(int(round(amount)), 150), 1)
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
        "is_successful": is_successful,
        "reason": reason
    }
    logs_collection.insert_one(log_entry)