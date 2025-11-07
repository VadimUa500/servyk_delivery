import os
from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from bson import ObjectId
from app.models.db import get_users_collection

UPLOAD_FOLDER = 'static/avatars'

class UploadAvatar(Resource):
    @jwt_required()
    def post(self):
        user_id = get_jwt_identity()
        users = get_users_collection()

        if 'avatar' not in request.files:
            return {'message': 'Файл не знайдено'}, 400

        file = request.files['avatar']
        if file.filename == '':
            return {'message': 'Порожнє ім’я файлу'}, 400

        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        filename = secure_filename(f"{user_id}_{file.filename}")
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        avatar_url = f'/static/avatars/{filename}'
        users.update_one({"_id": ObjectId(user_id)}, {"$set": {"avatar_url": avatar_url}})
        return {'message': 'Аватар оновлено', 'avatar_url': avatar_url}, 200
