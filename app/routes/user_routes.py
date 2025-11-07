from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.db import get_users_collection
from bson import ObjectId
from flask import request

class UserList(Resource):
    @jwt_required()
    def get(self):
        users = get_users_collection()
        result = []
        for u in users.find({}, {"password": 0}).sort("created_at", -1):
            result.append({
                "id": str(u["_id"]),
                "email": u.get("email"),
                "display_name": u.get("display_name",""),
                "role": u.get("role","client")
            })
        return {"users": result}, 200

class UserSearch(Resource):
    @jwt_required()
    def get(self):
        q = (request.args.get("q") or request.args.get("search") or "").strip()
        if not q:
            return {"users": []}, 200

        me = get_jwt_identity()
        users = get_users_collection()

        results = users.find({
            "display_name": {"$regex": q, "$options": "i"},
            "_id": {"$ne": ObjectId(me)}
        }).limit(10)

        out = []
        for u in results:
            out.append({
                "id": str(u["_id"]),
                "email": u.get("email",""),
                "display_name": u.get("display_name",""),
                "role": u.get("role","client")
            })
        return {"users": out}, 200
