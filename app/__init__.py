from dotenv import load_dotenv
from flask import Flask
from flask_restful import Api

from app.extensions import jwt, mongo


def create_app() -> Flask:
    """
    Створює та налаштовує Flask-застосунок
    програмної системи Delivery Helper.
    """

    # Змінні середовища повинні завантажитися
    # до читання конфігурації застосунку.
    load_dotenv()
    app = Flask(__name__)
    app.config.from_object("app.config.Config")
    app.json.ensure_ascii = False
    app.url_map.strict_slashes = False
    mongo.init_app(app)
    jwt.init_app(app)
    from app.database_indexes import ensure_database_indexes
    ensure_database_indexes(app)

    # Імпорти маршрутів виконуються всередині фабрики,
    # щоб зменшити ризик циклічних імпортів.
    from app.routes.admin_routes import (
        AdminUserUpdate,
        AdminUsersList,
    )
    from app.routes.auth_routes import Login, Register
    from app.routes.order_routes import (OrderAccept,OrderCancel,OrderCreate,OrderDelivered,OrderGet,OrderRoute,OrdersList,
    )
    from app.routes.profile_routes import UserProfile
    from app.routes.status_routes import (
        GeneralStatus,
        MyStatus,
        UserStatus,
    )
    from app.routes.tracking_routes import (
        CourierLocationUpdate,
        OrderTracking,
    )
    from app.routes.upload_avatar_route import UploadAvatar
    from app.routes.user_routes import UserList, UserSearch
    api = Api(app)

    api.add_resource(
        Register,
        "/register",
        endpoint="register",
    )
    api.add_resource(
        Login,
        "/login",
        endpoint="login",
    )

    # ------------------------------------------------------------------
    # Профіль і користувачі
    # ------------------------------------------------------------------

    api.add_resource(
        UserProfile,
        "/profile",
        endpoint="user_profile",
    )

    api.add_resource(
        UserList,
        "/users",
        endpoint="users_list",
    )

    api.add_resource(
        UserSearch,
        "/users/search",
        endpoint="users_search",
    )

    # ------------------------------------------------------------------
    # Замовлення
    # ------------------------------------------------------------------
    #
    # Один URL /orders використовується двома ресурсами:
    #
    # OrderCreate — POST /orders
    # OrdersList — GET /orders
    #
    # Різні endpoint-імена виключають конфлікт
    # внутрішніх назв маршрутів.
    # ------------------------------------------------------------------

    api.add_resource(
        OrderCreate,
        "/orders",
        endpoint="orders_create",
    )

    api.add_resource(
        OrdersList,
        "/orders",
        endpoint="orders_list",
    )

    api.add_resource(
        OrderGet,
        "/orders/<string:order_id>",
        endpoint="order_details",
    )

    api.add_resource(
        OrderRoute,
        "/orders/<string:order_id>/route",
        endpoint="order_route",
    )

    api.add_resource(
        OrderAccept,
        "/orders/accept/<string:order_id>",
        endpoint="order_accept",
    )

    api.add_resource(
        OrderDelivered,
        "/orders/delivered/<string:order_id>",
        endpoint="order_delivered",
    )

    api.add_resource(
        OrderCancel,
        "/orders/cancel/<string:order_id>",
        endpoint="order_cancel",
    )

    # ------------------------------------------------------------------
    # Живе відстеження кур’єра
    # ------------------------------------------------------------------

    api.add_resource(
        CourierLocationUpdate,
        "/courier/location",
        endpoint="courier_location_update",
    )

    api.add_resource(
        OrderTracking,
        "/orders/<string:order_id>/tracking",
        endpoint="order_tracking",
    )

    # ------------------------------------------------------------------
    # Адміністративні маршрути
    # ------------------------------------------------------------------

    api.add_resource(
        AdminUsersList,
        "/admin/users",
        endpoint="admin_users_list",
    )

    api.add_resource(
        AdminUserUpdate,
        "/admin/users/<string:user_id>",
        endpoint="admin_user_update",
    )

    # ------------------------------------------------------------------
    # Статуси користувачів
    # ------------------------------------------------------------------

    api.add_resource(
        GeneralStatus,
        "/status",
        endpoint="general_status",
    )

    api.add_resource(
        UserStatus,
        "/status/<string:user_id>",
        endpoint="user_status",
    )

    api.add_resource(
        MyStatus,
        "/me/status",
        endpoint="my_status",
    )

    # ------------------------------------------------------------------
    # Завантаження аватара
    # ------------------------------------------------------------------

    api.add_resource(
        UploadAvatar,
        "/upload-avatar",
        endpoint="upload_avatar",
    )

    # ------------------------------------------------------------------
    # Службовий маршрут перевірки сервера
    # ------------------------------------------------------------------

    @app.get("/")
    def api_root():
        return {
            "service": "Delivery Helper API",
            "status": "running",
        }, 200

    return app


