from pymongo import MongoClient
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["Geiqianbot"]
bank_collection = db["bank"]

# Delete all existing documents in the bank collection (optional)
bank_collection.delete_many({})

# Insert your reset bank document
bank_collection.insert_one({
    "balance": 10000,
    "last_update": datetime(2025, 10, 26, 12, 0, 0, tzinfo=timezone.utc),
    "lifetime_total": 30,
    "last_weekly_reset": datetime(2025, 10, 25, 12, 0, 0, tzinfo=timezone.utc)
})

print("✅ Bank collection reset successfully!")
