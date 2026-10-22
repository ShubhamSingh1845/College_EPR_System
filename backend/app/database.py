from collections.abc import Generator

from pymongo import MongoClient
from pymongo.database import Database

from app.config import settings

client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=3000)
database = client[settings.mongodb_database]


def get_database() -> Generator[Database, None, None]:
    yield database

