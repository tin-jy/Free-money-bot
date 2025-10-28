from pymongo import MongoClient
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["Geiqianbot"]
logs_collection = db["logs"]

result = logs_collection.delete_many({})
print(f"✅ Deleted {result.deleted_count} documents from logs_collection.")