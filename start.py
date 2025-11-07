from app import create_app
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from app.models.db import get_users_collection
from bson import ObjectId
from datetime import datetime

app = create_app()

@app.before_request
def update_last_seen():
    try:
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        if user_id:
            users = get_users_collection()
            users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"last_seen": datetime.utcnow()}}
            )
    except Exception:
        pass

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
