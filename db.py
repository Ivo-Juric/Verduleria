import sqlite3
import hashlib
from flask import g

DB_NAME = "database.db"

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_NAME)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop("db", None)
    if db:
        db.close()

def hash_pass(password):
    return hashlib.sha256(password.encode()).hexdigest()
