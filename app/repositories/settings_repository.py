import os
import sqlite3
from datetime import datetime


class SettingsRepository:
    def __init__(self, db_path):
        self.db_path = db_path

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS app_settings (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    language TEXT NOT NULL,
                    download_path TEXT NOT NULL,
                    proxy_type TEXT NOT NULL,
                    proxy_host TEXT NOT NULL,
                    proxy_port TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            existing = conn.execute("SELECT id FROM app_settings WHERE id = 1").fetchone()
            if not existing:
                now = datetime.utcnow().isoformat()
                conn.execute(
                    """
                    INSERT INTO app_settings (
                        id, language, download_path, proxy_type, proxy_host, proxy_port, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (1, "zh-CN", self._default_download_path(), "http", "127.0.0.1", "7890", now),
                )
            conn.commit()

    def _default_download_path(self):
        if os.name == "nt":
            drives = [f"{c}:\\" for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if os.path.exists(f"{c}:\\")]
            if drives:
                return sorted(drives)[-1]
        fallback = os.path.expanduser("~/Downloads")
        return fallback if os.path.exists(fallback) else os.path.expanduser("~")

    def get_settings(self):
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM app_settings WHERE id = 1").fetchone()
            return dict(row)

    def update_settings(self, payload):
        current = self.get_settings()
        merged = {
            "language": payload.get("language", current["language"]),
            "download_path": payload.get("download_path", current["download_path"]),
            "proxy_type": payload.get("proxy_type", current["proxy_type"]),
            "proxy_host": payload.get("proxy_host", current["proxy_host"]),
            "proxy_port": payload.get("proxy_port", current["proxy_port"]),
            "updated_at": datetime.utcnow().isoformat(),
        }
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE app_settings
                SET language = ?, download_path = ?, proxy_type = ?, proxy_host = ?, proxy_port = ?, updated_at = ?
                WHERE id = 1
                """,
                (
                    merged["language"],
                    merged["download_path"],
                    merged["proxy_type"],
                    merged["proxy_host"],
                    merged["proxy_port"],
                    merged["updated_at"],
                ),
            )
            conn.commit()
        return self.get_settings()
