from pymongo import MongoClient
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["Geiqianbot"]
logs_collection = db["logs"]

pipeline = [
    {"$match": {"is_successful": True}},
    {"$group": {
        "_id": "$user_id",
        "balance": {"$sum": "$amount"}
    }},
    {"$project": {
        "_id": 0,
        "user_id": "$_id",
        "balance": 1
    }}
]

results = list(logs_collection.aggregate(pipeline))

for r in results:
    print(r)