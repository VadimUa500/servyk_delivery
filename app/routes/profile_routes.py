from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.db import get_users_collection
from bson import ObjectId
from flask import request
from werkzeug.security import check_password_hash, generate_password_hash

class UserProfile(Resource):
    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        users = get_users_collection()
        u = users.find_one({"_id": ObjectId(user_id)})
        if not u:
            return {"message":"Користувача не знайдено"}, 404
        return {
            "id": str(u["_id"]),
            "email": u.get("email"),
            "display_name": u.get("display_name",""),
            "role": u.get("role","client"),
            "avatar_url": u.get("avatar_url","")
        }, 200

    @jwt_required()
    def put(self):
        user_id = get_jwt_identity()
        users = get_users_collection()
        data = request.get_json() or {}

        upd = {}
        if "display_name" in data: upd["display_name"] = data["display_name"]
        if "avatar_url" in data:   upd["avatar_url"]   = data["avatar_url"]

        if "old_password" in data and "new_password" in data:
            u = users.find_one({"_id": ObjectId(user_id)})
            if not u: return {"message":"Користувача не знайдено"}, 404
            if not check_password_hash(u["password"], data["old_password"]):
                return {"message":"Старий пароль неправильний"}, 401
            upd["password"] = generate_password_hash(data["new_password"])

        if not upd:
            return {"message":"Немає даних для оновлення"}, 400

        users.update_one({"_id": ObjectId(user_id)}, {"$set": upd})
        return {"message":"Профіль оновлено"}, 200
