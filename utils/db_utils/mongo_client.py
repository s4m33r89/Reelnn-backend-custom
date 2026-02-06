from pymongo import MongoClient
from config import DATABASE_URL


mongo_client = MongoClient(DATABASE_URL)


def get_database(db_name):  
    return mongo_client[db_name]


def close_connections():
    if mongo_client:
        mongo_client.close()