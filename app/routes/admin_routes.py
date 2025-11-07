from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt
from app.models.db import get_users_collection

def _role():
    claims = get_jwt() or {}
    return claims.get("role", "client")

class UsersAdminList(Resource):
    @jwt_required()
    def get(self):
        if _role() != "admin":
            return {"message":"forbidden"}, 403
        users = get_users_collection()
        out = []
        for u in users.find().sort("created_at", -1):
            out.append({
                "id": str(u["_id"]),
                "email": u.get("email"),
                "role": u.get("role","client"),
                "display_name": u.get("display_name",""),
                "is_active": u.get("is_active", True),
            })
        return {"users": out}, 200
