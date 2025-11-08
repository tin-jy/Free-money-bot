from pymongo import MongoClient
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["Geiqianbot"]
bank_collection = db["bank"]

bank_collection.delete_many({})

bank_collection.insert_one({
    "balance": 2,
    "lifetime_total": 174,
    "next_top_up": datetime(2025, 10, 29, 12, 0, 0, tzinfo=timezone.utc),
    "last_weekly_reset": datetime(2025, 10, 25, 12, 0, 0, tzinfo=timezone.utc)
})

print("✅ Bank collection reset successfully!")
