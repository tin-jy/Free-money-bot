from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone
from pymongo import ASCENDING, DESCENDING
import os

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["Geiqianbot"]
users_collection = db["users"]
button_game_collection = db["button_game"]

def log_button_game(game):
    user_id = game.get("user_id")
    button_game_collection.replace_one({"user_id": user_id, "in_progress": True}, game, upsert=True)

def get_button_game(user_id):
    return button_game_collection.find_one({
        "user_id": user_id,
        "in_progress": True
    })

def get_button_highscores():
    now = datetime.now(timezone.utc)

    # Calculate last Saturday 12:00 UTC
    days_since_saturday = (now.weekday() - 5) % 7
    last_saturday_noon = (now - timedelta(days=days_since_saturday)).replace(
        hour=12, minute=0, second=0, microsecond=0
    )

    pipeline_all_time = [
        {"$sort": {"score": DESCENDING, "timestamp": ASCENDING}},

        {"$group": {
            "_id": "$user_id",
            "user_name": {"$first": "$user_name"},
            "max_score": {"$first": "$score"},
            "achieved_at": {"$first": "$timestamp"}
        }},

        {"$sort": {"max_score": DESCENDING, "achieved_at": ASCENDING}}
    ]

    pipeline_weekly = [
        {"$match": {"timestamp": {"$gte": last_saturday_noon}}},

        {"$sort": {"score": DESCENDING, "timestamp": ASCENDING}},

        {"$group": {
            "_id": "$user_id",
            "user_name": {"$first": "$user_name"},
            "max_score": {"$first": "$score"},
            "achieved_at": {"$first": "$timestamp"}
        }},

        {"$sort": {"max_score": DESCENDING, "achieved_at": ASCENDING}}
    ]

    all_time_docs = list(button_game_collection.aggregate(pipeline_all_time))
    weekly_docs = list(button_game_collection.aggregate(pipeline_weekly))

    all_time = [
        {
            "user_id": doc["_id"],
            "user_name": doc["user_name"],
            "score": doc["max_score"]
        }
        for doc in all_time_docs
    ]
    weekly = [
        {
            "user_id": doc["_id"],
            "user_name": doc["user_name"],
            "score": doc["max_score"]
        }
        for doc in weekly_docs
    ]

    return all_time, weekly

def weekly_reset():
    result = button_game_collection.update_many(
        {"in_progress": True},
        {"$set": {"in_progress": False}}
    )