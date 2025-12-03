from flask_restful import Resource, reqparse
from flask_jwt_extended import create_access_token
from app.models.db import get_users_collection
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

register_parser = reqparse.RequestParser()
register_parser.add_argument('email', type=str, required=True, help="Введіть електронну пошту")
register_parser.add_argument('password', type=str, required=True, help="Введіть пароль")
register_parser.add_argument('display_name', type=str, required=False)
register_parser.add_argument(
    'role',
    type=str,
    required=False,
    choices=("client", "courier"),
    default="client"
)


login_parser = reqparse.RequestParser()
login_parser.add_argument('email', type=str, required=True, help="Введіть електронну пошту")
login_parser.add_argument('password', type=str, required=True, help="Введіть пароль")

class Register(Resource):
    def post(self):
        args = register_parser.parse_args()
        users = get_users_collection()
        email = (args["email"] or "").strip().lower()

        if users.find_one({"email": email}):
            return {"message": "Електронна пошта вже зареєстрована"}, 400

        user_data = {
            "email": email,
            "password": generate_password_hash(args["password"]),
            "display_name": args.get("display_name") or email.split("@")[0],
            "role": args.get("role") or "client",
            "is_active": True,
            "created_at": datetime.utcnow()
        }
        res = users.insert_one(user_data)
        return {"message": "Користувач зареєстрований", "id": str(res.inserted_id)}, 201

class Login(Resource):
    def post(self):
        args = login_parser.parse_args()
        users = get_users_collection()
        email = (args["email"] or "").strip().lower()

        user = users.find_one({"email": email})
        if not user or not check_password_hash(user["password"], args["password"]) or not user.get("is_active", True):
            return {"message": "Невірний email або пароль"}, 401

        identity = str(user["_id"])                 # як у тебе: зберігаємо лише id
        add_claims = {"role": user.get("role","client")}
        token = create_access_token(identity=identity, additional_claims=add_claims)
        return {"access_token": token, "role": add_claims["role"]}, 200
