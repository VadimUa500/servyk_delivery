import os
from datetime import datetime
from werkzeug.security import generate_password_hash
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/deliverydb")

client = MongoClient(MONGO_URI)
db = client.get_default_database()

def upsert_user(email, password, role, display_name):
    email = email.lower()
    existing = db.users.find_one({"email": email})
    if existing:
        print(f"[skip] {email} already exists")
        return existing["_id"]
    doc = {
        "email": email,
        "password": generate_password_hash(password),
        "role": role,
        "display_name": display_name,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "last_seen": datetime.utcnow()
    }
    res = db.users.insert_one(doc)
    print(f"[ok] created {email} ({role})")
    return res.inserted_id

def create_order(owner_id, address, description, phone, status="new", courier_id=None):
    now = datetime.utcnow()
    doc = {
        "owner_id": str(owner_id),
        "address": address,
        "description": description,
        "phone": phone,
        "status": status,
        "courier_id": str(courier_id) if courier_id else None,
        "created_at": now,
        "updated_at": now
    }
    res = db.orders.insert_one(doc)
    print(f"[ok] order {res.inserted_id} → {address} ({status})")
    return res.inserted_id

if __name__ == "__main__":
    admin_id = upsert_user("admin@test.com", "123456", "admin", "Admin")
    client_id = upsert_user("client@test.com", "123456", "client", "Client")
    courier_id = upsert_user("courier@test.com", "123456", "courier", "Courier")

    create_order(client_id, "Київ, Хрещатик 1", "Документи", "+380501234567", "new")
    create_order(client_id, "Львів, пл. Ринок 1", "Пакунок", "+380671234567", "in_progress", courier_id)
    create_order(client_id, "Одеса, Дерибасівська 10", "Книга", "+380931234567", "delivered", courier_id)

    print("✅ Seed complete.")
