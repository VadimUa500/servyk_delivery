from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from flask import request
from flask_jwt_extended import (
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from flask_restful import Resource
from pymongo import UpdateOne

from app.models.db import get_orders_collection


ALLOWED_TRAVEL_MODES = {
    "driving",
    "walking",
    "bicycling",
}

ALLOWED_STEP_TYPES = {
    "pickup",
    "delivery",
}


def _role() -> str:
    claims = get_jwt() or {}

    return str(
        claims.get("role", "client")
    ).strip().lower()


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def _to_float(
    value: Any,
    default: Optional[float] = None,
) -> Optional[float]:
    try:
        result = float(value)

        if result != result:
            return default

        if result in {
            float("inf"),
            float("-inf"),
        }:
            return default

        return result
    except (TypeError, ValueError):
        return default


def _to_int(
    value: Any,
    default: int = 0,
) -> int:
    try:
        return int(
            round(float(value))
        )
    except (TypeError, ValueError):
        return default


def _parse_object_id(
    value: Any,
) -> Optional[ObjectId]:
    try:
        return ObjectId(str(value))
    except Exception:
        return None


def _valid_coordinates(
    latitude: Optional[float],
    longitude: Optional[float],
) -> bool:
    if latitude is None or longitude is None:
        return False

    if latitude < -90 or latitude > 90:
        return False

    if longitude < -180 or longitude > 180:
        return False

    return not (
        latitude == 0.0
        and longitude == 0.0
    )


def _normalize_travel_mode(
    value: Any,
) -> str:
    mode = _normalize_text(value).lower()

    if mode in ALLOWED_TRAVEL_MODES:
        return mode

    return "driving"


def _normalize_step_type(
    value: Any,
) -> Optional[str]:
    step_type = _normalize_text(
        value
    ).lower()

    if step_type in ALLOWED_STEP_TYPES:
        return step_type

    return None


def _payload_value(
    payload: dict,
    *keys: str,
) -> Any:
    for key in keys:
        if key in payload:
            return payload[key]

    return None


def _same_identity(
    first: Any,
    second: Any,
) -> bool:
    if first is None or second is None:
        return False

    return str(first) == str(second)


def _datetime_to_iso(
    value: Any,
) -> Optional[str]:
    if not isinstance(value, datetime):
        return None

    if value.tzinfo is None:
        value = value.replace(
            tzinfo=timezone.utc
        )

    return value.astimezone(
        timezone.utc
    ).isoformat()


def _seconds_since(
    value: Any,
) -> Optional[int]:
    if not isinstance(value, datetime):
        return None

    if value.tzinfo is None:
        value = value.replace(
            tzinfo=timezone.utc
        )

    now = datetime.now(
        timezone.utc
    )

    seconds = int(
        (
            now
            - value.astimezone(
                timezone.utc
            )
        ).total_seconds()
    )

    return max(0, seconds)


def _safe_tracking(
    order: dict,
) -> dict:
    tracking = order.get("tracking")

    if isinstance(tracking, dict):
        return tracking

    return {}


def _identity_candidates(
    identity: str,
) -> list:
    candidates = [identity]

    object_id = _parse_object_id(
        identity
    )

    if object_id is not None:
        candidates.append(object_id)

    return candidates


class CourierLocationUpdate(Resource):
    @jwt_required()
    def post(self):
        identity = str(
            get_jwt_identity()
        )

        if _role() != "courier":
            return {
                "message": (
                    "Передавати координати "
                    "може лише кур’єр"
                )
            }, 403

        payload = request.get_json(
            silent=True
        )

        if not isinstance(payload, dict):
            return {
                "message": (
                    "Тіло запиту повинно "
                    "містити JSON"
                )
            }, 400

        latitude = _to_float(
            _payload_value(
                payload,
                "latitude",
                "lat",
            )
        )

        longitude = _to_float(
            _payload_value(
                payload,
                "longitude",
                "lng",
            )
        )

        if not _valid_coordinates(
            latitude,
            longitude,
        ):
            return {
                "message": (
                    "Передано некоректні "
                    "координати кур’єра"
                )
            }, 400

        accuracy = _to_float(
            _payload_value(
                payload,
                "accuracy",
            ),
            0.0,
        )

        speed_mps = _to_float(
            _payload_value(
                payload,
                "speed_mps",
                "speedMps",
                "speed",
            ),
            0.0,
        )

        heading = _to_float(
            _payload_value(
                payload,
                "heading",
            ),
            0.0,
        )

        accuracy = max(
            0.0,
            accuracy or 0.0,
        )

        speed_mps = max(
            0.0,
            speed_mps or 0.0,
        )

        heading = (
            heading or 0.0
        ) % 360

        travel_mode = (
            _normalize_travel_mode(
                _payload_value(
                    payload,
                    "travel_mode",
                    "travelMode",
                )
            )
        )

        current_step_type = (
            _normalize_step_type(
                _payload_value(
                    payload,
                    "current_step_type",
                    "currentStepType",
                )
            )
        )

        current_step_address = (
            _normalize_text(
                _payload_value(
                    payload,
                    "current_step_address",
                    "currentStepAddress",
                )
            )
        )

        current_step_order_id = (
            _normalize_text(
                _payload_value(
                    payload,
                    "current_step_order_id",
                    "currentStepOrderId",
                )
            )
        )

        raw_order_updates = (
            _payload_value(
                payload,
                "order_updates",
                "orderUpdates",
            )
        )

        if not isinstance(
            raw_order_updates,
            list,
        ):
            raw_order_updates = []

        updates_by_order_id = {}

        for raw_update in raw_order_updates:
            if not isinstance(
                raw_update,
                dict,
            ):
                continue

            order_id = _normalize_text(
                _payload_value(
                    raw_update,
                    "order_id",
                    "orderId",
                    "id",
                    "_id",
                )
            )

            object_id = _parse_object_id(
                order_id
            )

            if object_id is None:
                continue

            updates_by_order_id[
                str(object_id)
            ] = raw_update

        orders = get_orders_collection()

        base_query = {
            "courier_id": {
                "$in": _identity_candidates(
                    identity
                )
            },
            "status": "in_progress",
        }

        if updates_by_order_id:
            base_query["_id"] = {
                "$in": [
                    ObjectId(order_id)
                    for order_id
                    in updates_by_order_id
                ]
            }

        active_orders = list(
            orders.find(base_query)
        )

        if not active_orders:
            return {
                "message": (
                    "Не знайдено активних "
                    "замовлень цього кур’єра"
                )
            }, 404

        now = datetime.now(
            timezone.utc
        )

        mongo_updates = []

        for order in active_orders:
            order_id = str(
                order["_id"]
            )

            order_update = (
                updates_by_order_id.get(
                    order_id,
                    {},
                )
            )

            previous_tracking = (
                _safe_tracking(order)
            )

            remaining_distance = (
                _to_float(
                    _payload_value(
                        order_update,
                        "remaining_distance_km",
                        "remainingDistanceKm",
                    ),
                    _to_float(
                        previous_tracking.get(
                            "remaining_distance_km"
                        ),
                        _to_float(
                            order.get(
                                "distance_km"
                            ),
                            0.0,
                        ),
                    ),
                )
            )

            estimated_arrival = (
                _to_int(
                    _payload_value(
                        order_update,
                        "estimated_arrival_min",
                        "estimatedArrivalMin",
                    ),
                    _to_int(
                        previous_tracking.get(
                            "estimated_arrival_min"
                        ),
                        _to_int(
                            order.get(
                                "estimated_time_min"
                            ),
                            0,
                        ),
                    ),
                )
            )

            remaining_distance = max(
                0.0,
                remaining_distance or 0.0,
            )

            estimated_arrival = max(
                0,
                estimated_arrival,
            )

            tracking_document = {
                "active": True,
                "lat": latitude,
                "lng": longitude,
                "accuracy": accuracy,
                "speed_mps": speed_mps,
                "heading": heading,
                "travel_mode": travel_mode,
                "current_step_type": (
                    current_step_type
                ),
                "current_step_address": (
                    current_step_address
                ),
                "current_step_order_id": (
                    current_step_order_id
                ),
                "remaining_distance_km": round(
                    remaining_distance,
                    2,
                ),
                "estimated_arrival_min": (
                    estimated_arrival
                ),
                "updated_at": now,
            }

            mongo_updates.append(
                UpdateOne(
                    {
                        "_id": order["_id"],
                        "status": "in_progress",
                        "courier_id": {
                            "$in": (
                                _identity_candidates(
                                    identity
                                )
                            )
                        },
                    },
                    {
                        "$set": {
                            "tracking": (
                                tracking_document
                            ),
                            "travel_mode": (
                                travel_mode
                            ),
                            "updated_at": now,
                        }
                    },
                )
            )

        result = orders.bulk_write(
            mongo_updates,
            ordered=False,
        )

        return {
            "ok": True,
            "message": (
                "Позицію кур’єра оновлено"
            ),
            "matched_orders": (
                result.matched_count
            ),
            "updated_orders": (
                result.modified_count
            ),
            "travel_mode": travel_mode,
            "updated_at": (
                now.isoformat()
            ),
        }, 200


class OrderTracking(Resource):
    @jwt_required()
    def get(self, order_id):
        identity = str(
            get_jwt_identity()
        )

        role = _role()

        object_id = _parse_object_id(
            order_id
        )

        if object_id is None:
            return {
                "message": (
                    "Некоректний ID "
                    "замовлення"
                )
            }, 400

        orders = get_orders_collection()

        order = orders.find_one(
            {
                "_id": object_id,
            }
        )

        if order is None:
            return {
                "message": (
                    "Замовлення не знайдено"
                )
            }, 404

        owner_id = order.get(
            "owner_id"
        )

        courier_id = order.get(
            "courier_id"
        )

        has_access = False

        if role == "admin":
            has_access = True

        elif role == "client":
            has_access = _same_identity(
                owner_id,
                identity,
            )

        elif role == "courier":
            has_access = _same_identity(
                courier_id,
                identity,
            )

        if not has_access:
            return {
                "message": (
                    "Доступ до відстеження "
                    "цього замовлення заборонено"
                )
            }, 403

        status = str(
            order.get(
                "status",
                "new",
            )
        )

        tracking = _safe_tracking(
            order
        )

        travel_mode = (
            _normalize_travel_mode(
                tracking.get(
                    "travel_mode",
                    order.get(
                        "travel_mode",
                        "driving",
                    ),
                )
            )
        )

        latitude = _to_float(
            tracking.get("lat")
        )

        longitude = _to_float(
            tracking.get("lng")
        )

        tracking_available = (
            bool(tracking)
            and _valid_coordinates(
                latitude,
                longitude,
            )
        )

        seconds_since_update = (
            _seconds_since(
                tracking.get(
                    "updated_at"
                )
            )
        )

        tracking_active = bool(
            tracking.get(
                "active",
                False,
            )
        )

        is_live = (
            tracking_available
            and tracking_active
            and status == "in_progress"
            and seconds_since_update
            is not None
            and seconds_since_update <= 30
        )

        route_response = {
            "travel_mode": travel_mode,

            "current_step_type": (
                tracking.get(
                    "current_step_type"
                )
            ),
            "current_step_address": (
                tracking.get(
                    "current_step_address"
                )
            ),
            "current_step_order_id": (
                tracking.get(
                    "current_step_order_id"
                )
            ),

            "remaining_distance_km": (
                tracking.get(
                    "remaining_distance_km",
                    order.get(
                        "distance_km",
                        0.0,
                    ),
                )
            ),
            "estimated_arrival_min": (
                tracking.get(
                    "estimated_arrival_min",
                    order.get(
                        "estimated_time_min",
                        0,
                    ),
                )
            ),
        }

        if not tracking_available:
            message = (
                "Кур’єр ще не розпочав "
                "передавання геолокації"
            )

            if status == "new":
                message = (
                    "Замовлення ще очікує "
                    "прийняття кур’єром"
                )

            elif status == "delivered":
                message = (
                    "Доставку вже завершено"
                )

            elif status == "cancelled":
                message = (
                    "Замовлення скасовано"
                )

            return {
                "order_id": str(
                    order["_id"]
                ),
                "status": status,

                "tracking_available": False,
                "is_live": False,
                "seconds_since_update": None,

                "courier": {},
                "route": route_response,

                "message": message,
            }, 200

        return {
            "order_id": str(
                order["_id"]
            ),
            "status": status,

            "tracking_available": True,
            "is_live": is_live,
            "seconds_since_update": (
                seconds_since_update
            ),

            "courier": {
                "lat": latitude,
                "lng": longitude,
                "accuracy": _to_float(
                    tracking.get(
                        "accuracy"
                    ),
                    0.0,
                ),
                "speed_mps": _to_float(
                    tracking.get(
                        "speed_mps"
                    ),
                    0.0,
                ),
                "heading": _to_float(
                    tracking.get(
                        "heading"
                    ),
                    0.0,
                ),
                "updated_at": (
                    _datetime_to_iso(
                        tracking.get(
                            "updated_at"
                        )
                    )
                ),
            },

            "route": route_response,

            "message": (
                "Місцезнаходження "
                "кур’єра отримано"
                if is_live
                else (
                    "Остання позиція "
                    "кур’єра застаріла"
                )
            ),
        }, 200

