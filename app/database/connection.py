import os
from urllib.parse import quote_plus

class Config:
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:mti@localhost/mtidb'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default_secret_key')