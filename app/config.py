import os
from dotenv import load_dotenv

load_dotenv()

class Config(object):
    DB_SERVER = os.environ.get('DB_SERVER')
    DB_NAME = os.environ.get('DB_NAME')
    DB_USER = os.environ.get('DB_USER')
    DB_PASSWORD = os.environ.get('DB_PASSWORD')
    DB_PORT = os.environ.get('DB_PORT')
    SECRET_KEY = os.environ.get('SECRET_KEY')
