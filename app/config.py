import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=20)
    MONGO_URI = os.getenv('MONGO_URI', )  # або deliverydb
    DEBUG = os.getenv('DEBUG', True)
