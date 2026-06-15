import math
from datetime import datetime

from bson import ObjectId
from flask import request
from flask_jwt_extended import (
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from flask_restful import Resource, reqparse
from pymongo import ReturnDocument

from app.models.db import get_orders_collection


ALLOWED_ORDER_TYPES = {
    "parcel",
    "documents",
}

ALLOWED_TRAVEL_MODES = {
    "driving",
    "walking",
    "bicycling",
}


def _role() -> str:
    claims = get_jwt() or {}
    return str(claims.get("role", "client")).strip().lower()


def _parse_object_id(value):
    try:
        return ObjectId(str(value))
    except Exception:
        return None


def _to_float(value, default=None):
    try:
        number = float(value)

        if not math.isfinite(number):
            return default

        return number
    except (TypeError, ValueError):
        return default


def _to_int(value, default=0):
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return default


def _normalize_text(value) -> str:
    if value is None:
        return ""

    return str(value).strip()


def _valid_coordinates(latitude, longitude) -> bool:
    if latitude is None or longitude is None:
        return False

    if latitude < -90 or latitude > 90:
        return False

    if longitude < -180 or longitude > 180:
        return False

    if latitude == 0.0 and longitude == 0.0:
        return False

    return True


def _distance_km(lat1, lng1, lat2, lng2) -> float:
    earth_radius_km = 6371.0

    delta_latitude = math.radians(lat2 - lat1)
    delta_longitude = math.radians(lng2 - lng1)

    value = (
        math.sin(delta_latitude / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(delta_longitude / 2) ** 2
    )

    angular_distance = 2 * math.atan2(
        math.sqrt(value),
        math.sqrt(max(0.0, 1 - value)),
    )

    return round(
        earth_radius_km * angular_distance,
        2,
    )


def _estimated_time_minutes(
    distance_km: float,
    travel_mode: str,
) -> int:
    if distance_km <= 0:
        return 0

    average_speed_by_mode = {
        "driving": 30.0,
        "bicycling": 15.0,
        "walking": 5.0,
    }

    average_speed = average_speed_by_mode.get(
        travel_mode,
        30.0,
    )

    minutes = math.ceil(
        distance_km / average_speed * 60,
    )

    return max(1, minutes)


def _iso_datetime(value):
    if isinstance(value, datetime):
        return value.isoformat()

    return None


def _string_id(value):
    if value is None:
        return None

    return str(value)


def _serialize_order(order: dict) -> dict:
    tracking = order.get("tracking") or {}

    travel_mode = tracking.get(
        "travel_mode",
        order.get("travel_mode", "driving"),
    )

    if travel_mode not in ALLOWED_TRAVEL_MODES:
        travel_mode = "driving"

    return {
        "id": str(order["_id"]),
        "owner_id": _string_id(
            order.get("owner_id"),
        ),
        "courier_id": _string_id(
            order.get("courier_id"),
        ),

        "order_type": order.get(
            "order_type",
            "parcel",
        ),
        "status": order.get(
            "status",
            "new",
        ),
        "city": order.get(
            "city",
            "",
        ),

        "pickup_address": order.get(
            "pickup_address",
            "",
        ),
        "pickup_lat": order.get(
            "pickup_lat",
            0.0,
        ),
        "pickup_lng": order.get(
            "pickup_lng",
            0.0,
        ),

        "delivery_address": order.get(
            "delivery_address",
            "",
        ),
        "delivery_lat": order.get(
            "delivery_lat",
            0.0,
        ),
        "delivery_lng": order.get(
            "delivery_lng",
            0.0,
        ),

        "description": order.get(
            "description",
            "",
        ),
        "phone": order.get(
            "phone",
            "",
        ),
        "comment": order.get(
            "comment",
            "",
        ),

        "distance_km": order.get(
            "distance_km",
            0.0,
        ),
        "estimated_time_min": order.get(
            "estimated_time_min",
            0,
        ),
        "travel_mode": travel_mode,

        "tracking_available": bool(tracking),
        "tracking_updated_at": _iso_datetime(
            tracking.get("updated_at"),
        ),

        "created_at": _iso_datetime(
            order.get("created_at"),
        ),
        "updated_at": _iso_datetime(
            order.get("updated_at"),
        ),
        "accepted_at": _iso_datetime(
            order.get("accepted_at"),
        ),
        "delivered_at": _iso_datetime(
            order.get("delivered_at"),
        ),
        "cancelled_at": _iso_datetime(
            order.get("cancelled_at"),
        ),
    }


create_parser = reqparse.RequestParser()

create_parser.add_argument(
    "order_type",
    type=str,
    required=True,
    help="Тип замовлення обов’язковий",
)

create_parser.add_argument(
    "city",
    type=str,
    required=True,
    help="Місто обов’язкове",
)

create_parser.add_argument(
    "pickup_address",
    type=str,
    required=True,
    help="Адреса забору обов’язкова",
)

create_parser.add_argument(
    "pickup_lat",
    type=float,
    required=True,
    help="Широта точки забору обов’язкова",
)

create_parser.add_argument(
    "pickup_lng",
    type=float,
    required=True,
    help="Довгота точки забору обов’язкова",
)

create_parser.add_argument(
    "delivery_address",
    type=str,
    required=True,
    help="Адреса доставки обов’язкова",
)

create_parser.add_argument(
    "delivery_lat",
    type=float,
    required=True,
    help="Широта точки доставки обов’язкова",
)

create_parser.add_argument(
    "delivery_lng",
    type=float,
    required=True,
    help="Довгота точки доставки обов’язкова",
)

create_parser.add_argument(
    "description",
    type=str,
    required=False,
    default="",
)

create_parser.add_argument(
    "phone",
    type=str,
    required=False,
    default="",
)

create_parser.add_argument(
    "comment",
    type=str,
    required=False,
    default="",
)

create_parser.add_argument(
    "travel_mode",
    type=str,
    required=False,
    default="driving",
)


class OrderCreate(Resource):
    @jwt_required()
    def post(self):
        identity = get_jwt_identity()
        role = _role()

        if role != "client":
            return {
                "message": (
                    "Створювати замовлення "
                    "може лише клієнт"
                )
            }, 403

        args = create_parser.parse_args()

        order_type = _normalize_text(
            args.get("order_type"),
        ).lower()
        city = _normalize_text(
            args.get("city"),
        )
        pickup_address = _normalize_text(
            args.get("pickup_address"),
        )
        delivery_address = _normalize_text(
            args.get("delivery_address"),
        )
        travel_mode = _normalize_text(
            args.get("travel_mode"),
        ).lower()
        if order_type not in ALLOWED_ORDER_TYPES:
            return {
                "message": (
                    "Невірний тип замовлення. "
                    "Дозволено parcel або documents"
                )
            }, 400

        if travel_mode not in ALLOWED_TRAVEL_MODES:
            return {
                "message": (
                    "Невірний режим пересування. "
                    "Дозволено driving, walking "
                    "або bicycling"
                )
            }, 400

        if not city:
            return {
                "message": "Місто не може бути порожнім"
            }, 400

        if not pickup_address:
            return {
                "message": (
                    "Адреса забору не може бути порожньою"
                )
            }, 400

        if not delivery_address:
            return {
                "message": (
                    "Адреса доставки не може бути порожньою"
                )
            }, 400

        pickup_latitude = _to_float(
            args.get("pickup_lat"),
        )

        pickup_longitude = _to_float(
            args.get("pickup_lng"),
        )

        delivery_latitude = _to_float(
            args.get("delivery_lat"),
        )

        delivery_longitude = _to_float(
            args.get("delivery_lng"),
        )

        if not _valid_coordinates(
            pickup_latitude,
            pickup_longitude,
        ):
            return {
                "message": (
                    "Некоректні координати точки забору"
                )
            }, 400

        if not _valid_coordinates(
            delivery_latitude,
            delivery_longitude,
        ):
            return {
                "message": (
                    "Некоректні координати точки доставки"
                )
            }, 400

        distance = _distance_km(
            pickup_latitude,
            pickup_longitude,
            delivery_latitude,
            delivery_longitude,
        )

        estimated_time = _estimated_time_minutes(
            distance,
            travel_mode,
        )

        now = datetime.utcnow()
        order = {
            "owner_id": identity,
            "courier_id": None,
            "order_type": order_type,
            "status": "new",
            "city": city,
            "pickup_address": pickup_address,
            "pickup_lat": pickup_latitude,
            "pickup_lng": pickup_longitude,
            "delivery_address": delivery_address,
            "delivery_lat": delivery_latitude,
            "delivery_lng": delivery_longitude,
            "description": _normalize_text(
                args.get("description"),
            ),
            "phone": _normalize_text(
                args.get("phone"),
            ),
            "comment": _normalize_text(
                args.get("comment"),
            ),
            "distance_km": distance,
            "estimated_time_min": estimated_time,
            "travel_mode": travel_mode,
            "tracking": None,
            "created_at": now,
            "updated_at": now,
            "accepted_at": None,
            "delivered_at": None,
            "cancelled_at": None,
        }
        orders = get_orders_collection()
        result = orders.insert_one(order)
        order["_id"] = result.inserted_id

        return {
            "message": "Замовлення створено",
            "order": _serialize_order(order),
            "id": str(result.inserted_id),
        }, 201


class OrdersList(Resource):
    @jwt_required()
    def get(self):
        identity = get_jwt_identity()
        role = _role()

        tab = _normalize_text(
            request.args.get("tab"),
        ).lower()

        city = _normalize_text(
            request.args.get("city"),
        )

        if role == "client":
            if tab == "active":
                query = {
                    "owner_id": identity,
                    "status": {
                        "$in": [
                            "new",
                            "in_progress",
                        ]
                    },
                }

            elif tab == "delivered":
                query = {
                    "owner_id": identity,
                    "status": "delivered",
                }

            elif tab == "cancelled":
                query = {
                    "owner_id": identity,
                    "status": "cancelled",
                }

            else:
                query = {
                    "owner_id": identity,
                }

        elif role == "courier":
            if tab == "available":
                query = {
                    "status": "new",
                }

            elif tab == "active":
                query = {
                    "courier_id": identity,
                    "status": "in_progress",
                }

            elif tab == "delivered":
                query = {
                    "courier_id": identity,
                    "status": "delivered",
                }

            else:
                query = {
                    "$or": [
                        {
                            "status": "new",
                        },
                        {
                            "courier_id": identity,
                        },
                    ]
                }

            if city:
                query["city"] = city

        elif role == "admin":
            query = {}

            if tab in {
                "new",
                "in_progress",
                "delivered",
                "cancelled",
            }:
                query["status"] = tab

            if city:
                query["city"] = city

        else:
            return {
                "message": "Невідома роль користувача"
            }, 403

        orders = get_orders_collection()

        cursor = (
            orders.find(query)
            .sort("created_at", -1)
            .limit(200)
        )

        return {
            "orders": [
                _serialize_order(order)
                for order in cursor
            ]
        }, 200


class OrderGet(Resource):
    @jwt_required()
    def get(self, order_id):
        identity = get_jwt_identity()
        role = _role()

        object_id = _parse_object_id(order_id)

        if object_id is None:
            return {
                "message": "Некоректний ID замовлення"
            }, 400

        orders = get_orders_collection()
        order = orders.find_one(
            {
                "_id": object_id,
            }
        )

        if not order:
            return {
                "message": "Замовлення не знайдено"
            }, 404

        has_access = False

        if role == "admin":
            has_access = True

        elif role == "client":
            has_access = (
                order.get("owner_id") == identity
            )

        elif role == "courier":
            has_access = (
                order.get("status") == "new"
                or order.get("courier_id") == identity
            )

        if not has_access:
            return {
                "message": (
                    "Доступ до цього замовлення заборонено"
                )
            }, 403

        return _serialize_order(order), 200


class OrderAccept(Resource):
    @jwt_required()
    def post(self, order_id):
        identity = get_jwt_identity()
        role = _role()
        if role != "courier":
            return {
                "message": (
                    "Приймати замовлення "
                    "може лише кур’єр"
                )
            }, 403
        object_id = _parse_object_id(order_id)

        if object_id is None:
            return {
                "message": "Некоректний ID замовлення"
            }, 400
        orders = get_orders_collection()
        now = datetime.utcnow()
        updated_order = orders.find_one_and_update(
            {
                "_id": object_id,
                "status": "new",
            },
            {
                "$set": {
                    "status": "in_progress",
                    "courier_id": identity,
                    "accepted_at": now,
                    "updated_at": now,
                    "tracking": None,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        if updated_order is None:
            existing_order = orders.find_one(
                {
                    "_id": object_id,
                }
            )
            if not existing_order:
                return {
                    "message": "Замовлення не знайдено"
                }, 404
            return {
                "message": (
                    "Замовлення вже прийняте "
                    "або більше недоступне"
                )
            }, 409
        return {
            "ok": True,
            "message": "Замовлення прийнято",
            "order": _serialize_order(
                updated_order,
            ),
        }, 200


class OrderDelivered(Resource):
    @jwt_required()
    def post(self, order_id):
        identity = get_jwt_identity()
        role = _role()

        if role not in {
            "courier",
            "admin",
        }:
            return {
                "message": (
                    "Завершувати доставку "
                    "може лише кур’єр"
                )
            }, 403

        object_id = _parse_object_id(order_id)

        if object_id is None:
            return {
                "message": "Некоректний ID замовлення"
            }, 400

        query = {
            "_id": object_id,
            "status": "in_progress",
        }

        if role == "courier":
            query["courier_id"] = identity

        orders = get_orders_collection()
        now = datetime.utcnow()

        updated_order = orders.find_one_and_update(
            query,
            {
                "$set": {
                    "status": "delivered",
                    "estimated_time_min": 0,
                    "delivered_at": now,
                    "updated_at": now,
                    "tracking.active": False,
                    "tracking.remaining_distance_km": 0,
                    "tracking.estimated_arrival_min": 0,
                    "tracking.updated_at": now,
                }
            },
            return_document=ReturnDocument.AFTER,
        )

        if updated_order is None:
            existing_order = orders.find_one(
                {
                    "_id": object_id,
                }
            )
            if not existing_order:
                return {
                    "message": "Замовлення не знайдено"
                }, 404
            if (
                role == "courier"
                and existing_order.get("courier_id")
                != identity
            ):
                return {
                    "message": (
                        "Замовлення закріплене "
                        "за іншим кур’єром"
                    )
                }, 403
            return {
                "message": (
                    "Замовлення не перебуває "
                    "у процесі доставки"
                )
            }, 409
        return {
            "ok": True,
            "message": "Замовлення доставлено",
            "order": _serialize_order(
                updated_order,
            ),
        }, 200


class OrderCancel(Resource):
    @jwt_required()
    def post(self, order_id):
        identity = get_jwt_identity()
        role = _role()

        object_id = _parse_object_id(order_id)

        if object_id is None:
            return {
                "message": "Некоректний ID замовлення"
            }, 400

        orders = get_orders_collection()

        existing_order = orders.find_one(
            {
                "_id": object_id,
            }
        )

        if not existing_order:
            return {
                "message": "Замовлення не знайдено"
            }, 404

        current_status = existing_order.get(
            "status",
            "new",
        )

        if current_status in {
            "delivered",
            "cancelled",
        }:
            return {
                "message": (
                    "Завершене або скасоване "
                    "замовлення змінити неможливо"
                )
            }, 409

        if role == "client":
            if (
                existing_order.get("owner_id")
                != identity
            ):
                return {
                    "message": (
                        "Скасувати можна лише "
                        "власне замовлення"
                    )
                }, 403

            if current_status != "new":
                return {
                    "message": (
                        "Клієнт може скасувати "
                        "лише нове замовлення"
                    )
                }, 409

        elif role != "admin":
            return {
                "message": (
                    "У вас немає дозволу "
                    "скасовувати замовлення"
                )
            }, 403

        now = datetime.utcnow()

        updated_order = orders.find_one_and_update(
            {
                "_id": object_id,
                "status": current_status,
            },
            {
                "$set": {
                    "status": "cancelled",
                    "cancelled_at": now,
                    "updated_at": now,
                    "tracking.active": False,
                    "tracking.updated_at": now,
                }
            },
            return_document=ReturnDocument.AFTER,
        )

        if updated_order is None:
            return {
                "message": (
                    "Статус замовлення вже змінився. "
                    "Оновіть список"
                )
            }, 409

        return {
            "ok": True,
            "message": "Замовлення скасовано",
            "order": _serialize_order(
                updated_order,
            ),
        }, 200


class OrderRoute(Resource):
    @jwt_required()
    def get(self, order_id):
        identity = get_jwt_identity()
        role = _role()

        object_id = _parse_object_id(order_id)

        if object_id is None:
            return {
                "message": "Некоректний ID замовлення"
            }, 400

        orders = get_orders_collection()

        order = orders.find_one(
            {
                "_id": object_id,
            }
        )

        if not order:
            return {
                "message": "Замовлення не знайдено"
            }, 404

        has_access = False

        if role == "admin":
            has_access = True

        elif role == "client":
            has_access = (
                order.get("owner_id") == identity
            )

        elif role == "courier":
            has_access = (
                order.get("status") == "new"
                or order.get("courier_id") == identity
            )

        if not has_access:
            return {
                "message": (
                    "Маршрут цього замовлення "
                    "недоступний"
                )
            }, 403

        tracking = order.get("tracking") or {}

        travel_mode = tracking.get(
            "travel_mode",
            order.get("travel_mode", "driving"),
        )

        if travel_mode not in ALLOWED_TRAVEL_MODES:
            travel_mode = "driving"

        return {
            "order_id": str(order["_id"]),
            "status": order.get(
                "status",
                "new",
            ),
            "travel_mode": travel_mode,

            "pickup": {
                "address": order.get(
                    "pickup_address",
                    "",
                ),
                "lat": order.get(
                    "pickup_lat",
                    0.0,
                ),
                "lng": order.get(
                    "pickup_lng",
                    0.0,
                ),
            },

            "delivery": {
                "address": order.get(
                    "delivery_address",
                    "",
                ),
                "lat": order.get(
                    "delivery_lat",
                    0.0,
                ),
                "lng": order.get(
                    "delivery_lng",
                    0.0,
                ),
            },

            "distance_km": order.get(
                "distance_km",
                0.0,
            ),
            "estimated_time_min": order.get(
                "estimated_time_min",
                0,
            ),

            "current_step_type": tracking.get(
                "current_step_type",
            ),
            "current_step_address": tracking.get(
                "current_step_address",
            ),
            "remaining_distance_km": tracking.get(
                "remaining_distance_km",
            ),
            "estimated_arrival_min": tracking.get(
                "estimated_arrival_min",
                order.get("estimated_time_min", 0),
            ),
        }, 200
