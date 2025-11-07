from flask import Flask
from flask_restful import Api
from dotenv import load_dotenv
import os

from app.extensions import mongo, jwt

def create_app():
    load_dotenv()
    print("DEBUG MONGO_URI:", os.getenv("MONGO_URI"))

    app = Flask(__name__)
    app.config.from_object('app.config.Config')

    mongo.init_app(app)
    jwt.init_app(app)

    # ===== Імпорт НАШИХ маршрутів (Delivery-helper) =====
    from app.routes.auth_routes import Register, Login
    from app.routes.profile_routes import UserProfile
    from app.routes.user_routes import UserList, UserSearch

    # нові — замість чатів/повідомлень:
    from app.routes.order_routes import (
        OrderCreate, OrdersList, OrderAccept, OrderDelivered, OrderCancel, OrderGet
    )
    from app.routes.admin_routes import UsersAdminList
    from app.routes.status_routes import GeneralStatus, UserStatus, MyStatus
    from app.routes.upload_avatar_route import UploadAvatar

    api = Api(app)

    # auth
    api.add_resource(Register, "/register")
    api.add_resource(Login, "/login")

    # profile & users
    api.add_resource(UserProfile, "/profile")
    api.add_resource(UserList, "/users")
    api.add_resource(UserSearch, "/users/search")

    # orders
    api.add_resource(OrderCreate,   "/orders")                      # POST
    api.add_resource(OrdersList,    "/orders")                      # GET(список по ролі)
    api.add_resource(OrderGet,      "/orders/<string:order_id>")     # GET   (деталі)
    api.add_resource(OrderAccept,   "/orders/accept/<string:order_id>")     # POST (courier/admin)
    api.add_resource(OrderDelivered,"/orders/delivered/<string:order_id>")  # POST (courier/admin)
    api.add_resource(OrderCancel,   "/orders/cancel/<string:order_id>")     # POST (owner/admin)

    # admin
    api.add_resource(UsersAdminList, "/admin/users")

    # status & uploads
    api.add_resource(GeneralStatus, '/status')
    api.add_resource(UserStatus,    '/status/<string:user_id>')
    api.add_resource(MyStatus,      '/me/status')
    api.add_resource(UploadAvatar,  '/upload-avatar')

    return app
