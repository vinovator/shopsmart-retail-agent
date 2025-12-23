# app/utils/db.py

from sqlmodel import create_engine, Session

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sqlite_file_name = os.path.join(BASE_DIR, "database.db")
sqlite_url = f"sqlite:///{sqlite_file_name}"

# check_same_thread=False is only needed for SQLite. It's not needed for other databases.
engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

def get_session():
    # Dependency to yield a database session
    with Session(engine) as session:
        yield session