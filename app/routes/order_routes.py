from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.models.db import get_orders_collection
from bson import ObjectId
from datetime import datetime

create_parser = reqparse.RequestParser()
create_parser.add_argument('address', type=str, required=True, help="Адреса обов'язкова")
create_parser.add_argument('description', type=str, required=False, default="")
create_parser.add_argument('phone', type=str, required=False, default="")

def _role():
    claims = get_jwt() or {}
    return claims.get("role", "client")

class OrderCreate(Resource):
    @jwt_required()
    def post(self):
        ident = get_jwt_identity()
        args = create_parser.parse_args()
        orders = get_orders_collection()
        now = datetime.utcnow()

        order = {
            "owner_id": ident,
            "address": args["address"],
            "description": args.get("description") or "",
            "phone": args.get("phone") or "",
            "status": "new",                    # new | in_progress | delivered | cancelled
            "courier_id": None,
            "created_at": now,
            "updated_at": now
        }
        res = orders.insert_one(order)
        return {"id": str(res.inserted_id)}, 201

class OrdersList(Resource):
    @jwt_required()
    def get(self):
        ident = get_jwt_identity()
        role = _role()
        orders = get_orders_collection()

        if role == "client":
            q = {"owner_id": ident}
        elif role == "courier":
            q = {"$or": [{"status":"new"}, {"courier_id": ident}]}
        else:  # admin
            q = {}

        cur = orders.find(q).sort("created_at", -1)
        out = []
        for o in cur:
            out.append({
                "id": str(o["_id"]),
                "address": o.get("address",""),
                "status": o.get("status","new"),
                "owner_id": o.get("owner_id"),
                "courier_id": o.get("courier_id"),
                "created_at": o.get("created_at").isoformat() if o.get("created_at") else None,
                "updated_at": o.get("updated_at").isoformat() if o.get("updated_at") else None,
            })
        return {"orders": out}, 200

class OrderGet(Resource):
    @jwt_required()
    def get(self, order_id):
        ident = get_jwt_identity()
        role = _role()
        orders = get_orders_collection()
        o = orders.find_one({"_id": ObjectId(order_id)})
        if not o:
            return {"message":"Замовлення не знайдене"}, 404

        # доступ: власник, призначений кур'єр, або адмін
        if role != "admin" and not (o.get("owner_id")==ident or o.get("courier_id")==ident):
            return {"message":"forbidden"}, 403

        o["id"] = str(o.pop("_id"))
        if o.get("created_at"): o["created_at"] = o["created_at"].isoformat()
        if o.get("updated_at"): o["updated_at"] = o["updated_at"].isoformat()
        return o, 200

class OrderAccept(Resource):
    @jwt_required()
    def post(self, order_id):
        ident = get_jwt_identity()
        role = _role()
        if role not in ("courier","admin"):
            return {"message":"forbidden"}, 403

        orders = get_orders_collection()
        o = orders.find_one({"_id": ObjectId(order_id)})
        if not o or o.get("status") != "new":
            return {"message":"order unavailable"}, 400

        orders.update_one({"_id": o["_id"]}, {"$set": {
            "status": "in_progress",
            "courier_id": ident,
            "updated_at": datetime.utcnow()
        }})
        return {"ok": True}, 200

class OrderDelivered(Resource):
    @jwt_required()
    def post(self, order_id):
        ident = get_jwt_identity()
        role = _role()
        if role not in ("courier","admin"):
            return {"message":"forbidden"}, 403

        orders = get_orders_collection()
        o = orders.find_one({"_id": ObjectId(order_id)})
        if not o or o.get("status") != "in_progress":
            return {"message":"wrong status"}, 400

        # якщо кур'єр — має бути призначений на це замовлення
        if role == "courier" and o.get("courier_id") != ident:
            return {"message":"forbidden"}, 403

        orders.update_one({"_id": o["_id"]}, {"$set": {
            "status": "delivered",
            "updated_at": datetime.utcnow()
        }})
        return {"ok": True}, 200

class OrderCancel(Resource):
    @jwt_required()
    def post(self, order_id):
        ident = get_jwt_identity()
        role = _role()
        orders = get_orders_collection()
        o = orders.find_one({"_id": ObjectId(order_id)})
        if not o:
            return {"message":"Замовлення не знайдене"}, 404

        # скасувати може власник (поки "new") або адмін будь-коли
        if role == "admin":
            pass
        else:
            if o.get("owner_id") != ident or o.get("status") not in ("new",):
                return {"message":"forbidden"}, 403

        orders.update_one({"_id": o["_id"]}, {"$set": {
            "status": "cancelled",
            "updated_at": datetime.utcnow()
        }})
        return {"ok": True}, 200
