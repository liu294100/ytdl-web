import os


class Config:
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    SQLITE_DB_PATH = os.path.join(DATA_DIR, "app.db")
    TASK_MAX_WORKERS = 3
