from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.db import get_users_collection
from bson import ObjectId
from datetime import datetime, timedelta

class GeneralStatus(Resource):
    def get(self):
        return {"status":"ok"}, 200

class UserStatus(Resource):
    @jwt_required()
    def get(self, user_id):
        users = get_users_collection()
        u = users.find_one({"_id": ObjectId(user_id)})
        if not u:
            return {"message":"Користувача не знайдено"}, 404
        last_seen = u.get("last_seen")
        online = False
        if last_seen:
            online = datetime.utcnow() - last_seen < timedelta(seconds=60)
        return {
            "user_id": str(u["_id"]),
            "online": online,
            "last_seen": last_seen.isoformat() if last_seen else None
        }, 200

class MyStatus(Resource):
    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        users = get_users_collection()
        u = users.find_one({"_id": ObjectId(user_id)})
        if not u:
            return {"message":"Користувача не знайдено"}, 404
        last_seen = u.get("last_seen")
        online = False
        if last_seen:
            online = datetime.utcnow() - last_seen < timedelta(seconds=60)
        return {
            "user_id": str(u["_id"]),
            "online": online,
            "last_seen": last_seen.isoformat() if last_seen else None
        }, 200
