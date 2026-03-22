import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from app.config import Config


class TaskManager:
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=Config.TASK_MAX_WORKERS, thread_name_prefix="ytdl")
        self._tasks = {}
        self._lock = threading.Lock()

    def create_task(self):
        task_id = uuid.uuid4().hex
        task = {
            "task_id": task_id,
            "status": "queued",
            "progress": 0.0,
            "status_text": "queued",
            "logs": [],
            "error": "",
            "files": [],
            "cancel_requested": False,
            "updated_at": time.time(),
        }
        with self._lock:
            self._tasks[task_id] = task
        return task_id

    def submit(self, task_id, fn, *args):
        return self._executor.submit(fn, task_id, *args)

    def append_log(self, task_id, message):
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return
            task["logs"].append(line)
            if len(task["logs"]) > 1500:
                task["logs"] = task["logs"][-1200:]
            task["updated_at"] = time.time()

    def update(self, task_id, **kwargs):
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return
            task.update(kwargs)
            task["updated_at"] = time.time()

    def get(self, task_id):
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None
            return {
                "task_id": task["task_id"],
                "status": task["status"],
                "progress": float(task["progress"]),
                "status_text": task["status_text"],
                "logs": list(task["logs"][-400:]),
                "error": task["error"],
                "files": list(task.get("files") or []),
                "file_count": len(task.get("files") or []),
            }

    def get_files(self, task_id):
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None
            return list(task.get("files") or [])

    def cancel(self, task_id):
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            task["cancel_requested"] = True
            task["status_text"] = "cancelling"
            task["updated_at"] = time.time()
            return True

    def is_cancel_requested(self, task_id):
        with self._lock:
            task = self._tasks.get(task_id)
            return bool(task and task.get("cancel_requested"))


task_manager = TaskManager()
