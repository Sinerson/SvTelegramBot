# Config parameters
import os

from dotenv import load_dotenv

load_dotenv()

DRIVER = os.getenv('DRIVER')
SERVER = os.getenv('SERVER')
PORT = os.getenv('PORT')
DB_NAME = os.getenv('DB_NAME')
USER = os.getenv('USER')
PASSW = os.getenv('PASSW')
LANGUAGE = os.getenv('LANGUAGE')
CONN_LIFETIME = os.getenv('CONN_LIFETIME')
IDLE = os.getenv('IDLE')
AUTOCOMMIT = os.getenv('AUTOCOMMIT')
CLIENT_HOST_NAME = os.getenv('CLIENT_HOST_NAME_DEV')
CLIENT_HOST_PROC = os.getenv('CLIENT_HOST_PROC')
APPLICATION_NAME = os.getenv('APPLICATION_NAME_DEV')
TOKEN = os.getenv('TOKEN_DEV')
CHANNEL_ID = os.getenv('CHANNEL_ID')
BANK_TOKEN = os.getenv('BANK_TOKEN')
USERS_ID_LIST = os.getenv('USERS_ID_LIST')
ADMIN_ID_LIST = os.getenv('ADMIN_USERS_LIST')

