from typing import Optional

from flask import Flask
from pymongo import ASCENDING, DESCENDING
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from app.extensions import mongo


def _create_index(
    app: Flask,
    collection: Collection,
    keys,
    *,
    name: str,
    unique: bool = False,
    sparse: bool = False,
) -> Optional[str]:
    """
    Створює індекс і не зупиняє запуск сервера,
    якщо в наявних даних є проблема.

    Повертає назву створеного або вже наявного індексу.
    """

    try:
        return collection.create_index(
            keys,
            name=name,
            unique=unique,
            sparse=sparse,
        )
    except PyMongoError as error:
        app.logger.warning(
            "Не вдалося створити індекс %s для колекції %s: %s",
            name,
            collection.name,
            error,
        )

        return None


def ensure_database_indexes(app: Flask) -> None:
    """
    Створює індекси MongoDB, які відповідають
    основним запитам програмної системи Delivery Helper.

    Функцію потрібно викликати після mongo.init_app(app).
    Повторний виклик є безпечним: MongoDB не створює
    однаковий індекс повторно.
    """

    with app.app_context():
        database = mongo.db

        if database is None:
            app.logger.warning(
                "MongoDB не підключена. Індекси не створено."
            )
            return

        users = database.get_collection("users")
        orders = database.get_collection("orders")

        created_indexes = []

        # --------------------------------------------------------------
        # Колекція users
        # --------------------------------------------------------------

        # Електронна пошта використовується під час авторизації.
        # unique=True не дозволяє створити два облікові записи
        # з однаковою електронною адресою.
        email_index = _create_index(
            app,
            users,
            [
                ("email", ASCENDING),
            ],
            name="uq_users_email",
            unique=True,
            sparse=True,
        )

        if email_index is not None:
            created_indexes.append(email_index)

        # Пошук і фільтрація користувачів за роллю
        # та станом облікового запису.
        role_index = _create_index(
            app,
            users,
            [
                ("role", ASCENDING),
                ("is_active", ASCENDING),
            ],
            name="idx_users_role_active",
        )

        if role_index is not None:
            created_indexes.append(role_index)

        # Сортування користувачів за останньою активністю.
        last_seen_index = _create_index(
            app,
            users,
            [
                ("last_seen", DESCENDING),
            ],
            name="idx_users_last_seen",
        )

        if last_seen_index is not None:
            created_indexes.append(last_seen_index)

        # --------------------------------------------------------------
        # Колекція orders
        # --------------------------------------------------------------

        # Активні, доставлені та скасовані замовлення клієнта.
        owner_orders_index = _create_index(
            app,
            orders,
            [
                ("owner_id", ASCENDING),
                ("status", ASCENDING),
                ("created_at", DESCENDING),
            ],
            name="idx_orders_owner_status_created",
        )

        if owner_orders_index is not None:
            created_indexes.append(owner_orders_index)

        # Активні та завершені замовлення конкретного кур’єра.
        courier_orders_index = _create_index(
            app,
            orders,
            [
                ("courier_id", ASCENDING),
                ("status", ASCENDING),
                ("created_at", DESCENDING),
            ],
            name="idx_orders_courier_status_created",
        )

        if courier_orders_index is not None:
            created_indexes.append(courier_orders_index)

        # Список доступних заявок за містом.
        available_orders_index = _create_index(
            app,
            orders,
            [
                ("status", ASCENDING),
                ("city", ASCENDING),
                ("created_at", DESCENDING),
            ],
            name="idx_orders_status_city_created",
        )

        if available_orders_index is not None:
            created_indexes.append(available_orders_index)

        # Отримання останніх оновлень GPS-відстеження.
        tracking_index = _create_index(
            app,
            orders,
            [
                ("tracking.updated_at", DESCENDING),
            ],
            name="idx_orders_tracking_updated",
            sparse=True,
        )

        if tracking_index is not None:
            created_indexes.append(tracking_index)

        # Додатковий індекс для перевірки типів замовлень.
        order_type_index = _create_index(
            app,
            orders,
            [
                ("order_type", ASCENDING),
            ],
            name="idx_orders_order_type",
        )

        if order_type_index is not None:
            created_indexes.append(order_type_index)

        app.logger.info(
            "Перевірено індекси MongoDB: %s",
            ", ".join(created_indexes)
            if created_indexes
            else "жоден індекс не створено",
        )

