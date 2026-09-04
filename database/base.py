"""Compatibility exports for database code that imports ``database.base``."""

from database.init_db import init_db
from database.session import engine, get_session

__all__ = ["engine", "get_session", "init_db"]
