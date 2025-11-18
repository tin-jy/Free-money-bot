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
users_collection = db["users"]
lucky9_collection = db["dropball"]

def get_live_game(user_id: int):
    return lucky9_collection.find_one({
        "user_id": user_id,
        "in_progress": True
    })

def update_game(game: dict):
    result = lucky9_collection.replace_one({
        "user_id": game.get("user_id"),
        "in_progress": True
    }, replacement=game, upsert=True)