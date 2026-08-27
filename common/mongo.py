"""
Shared MongoDB connection for the reviews collection.

Reviews are stored in MongoDB instead of MySQL because they are small,
self-contained documents with no relational structure to enforce (a review
never needs a JOIN) - a document store fits that shape more naturally than
a relational table, and demonstrates picking the right storage engine per
workload (polyglot persistence) rather than forcing every entity into one
database.
"""

import os

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "travel_booking_reviews")

# A single MongoClient manages its own internal connection pool, so it is
# created once at import time and reused - unlike SQLAlchemy sessions,
# Mongo clients are meant to be long-lived and shared.
_client = MongoClient(MONGO_URL)
_database = _client[MONGO_DB]


def get_reviews_collection():
    """Return the shared 'reviews' collection used by all services."""
    return _database["reviews"]
