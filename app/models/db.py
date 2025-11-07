from app.extensions import mongo
from pymongo import ASCENDING

def init_mongo(app):
    mongo.init_app(app)

def get_users_collection():
    return mongo.db.users

def get_orders_collection():
    return mongo.db.orders

def ensure_indexes():
    try:
        u = get_users_collection()
        u.create_index([("email", ASCENDING)], unique=True)
        o = get_orders_collection()
        o.create_index([("created_at", ASCENDING)])
        o.create_index([("status", ASCENDING)])
    except Exception as e:
        print("Index creation skipped (Mongo not yet initialized):", e)
