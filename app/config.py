import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'super-secret-key')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-super-secret')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=20)
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/securapp')  # або deliverydb — як зручно
    DEBUG = os.getenv('DEBUG', True)
