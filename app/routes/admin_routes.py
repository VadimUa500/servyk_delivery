from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from flask import request
from bson import ObjectId

from app.models.db import get_users_collection


def _is_admin() -> bool:
    claims = get_jwt() or {}
    return claims.get("role") == "admin"


class AdminUsersList(Resource):
    """Список усіх користувачів (тільки для admin)."""

    @jwt_required()
    def get(self):
        if not _is_admin():
            return {"message": "Доступ лише для адміністратора"}, 403

        users = get_users_collection()
        result = []
        for u in users.find().sort("created_at", -1):
            result.append({
                "id": str(u["_id"]),
                "email": u.get("email", ""),
                "display_name": u.get("display_name", ""),
                "role": u.get("role", "client"),
                "is_active": u.get("is_active", True),
                "created_at": u.get("created_at").isoformat() if u.get("created_at") else None,
            })
        return {"users": result}, 200


class AdminUserUpdate(Resource):
    """
    Оновлення даних користувача адміном:
    PUT /admin/users/<user_id>
    body: { "role": "courier", "is_active": true }
    """

    @jwt_required()
    def put(self, user_id: str):
        if not _is_admin():
            return {"message": "Доступ лише для адміністратора"}, 403

        users = get_users_collection()
        try:
            oid = ObjectId(user_id)
        except Exception:
            return {"message": "Некоректний ідентифікатор користувача"}, 400

        data = request.get_json() or {}
        upd = {}

        # зміна ролі
        if "role" in data:
            role = str(data["role"]).strip()
            if role not in ("client", "courier", "admin"):
                return {"message": "Неприпустима роль"}, 400
            upd["role"] = role

        # блокування / розблокування
        if "is_active" in data:
            upd["is_active"] = bool(data["is_active"])

        if not upd:
            return {"message": "Немає полів для оновлення"}, 400

        res = users.update_one({"_id": oid}, {"$set": upd})
        if res.matched_count == 0:
            return {"message": "Користувача не знайдено"}, 404

        u = users.find_one({"_id": oid})
        return {
            "message": "Дані користувача оновлено",
            "user": {
                "id": str(u["_id"]),
                "email": u.get("email", ""),
                "display_name": u.get("display_name", ""),
                "role": u.get("role", "client"),
                "is_active": u.get("is_active", True),
            }
        }, 200
