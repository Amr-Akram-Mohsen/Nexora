import json
import os
import uuid
from datetime import datetime
from flask import current_app

class TaskTracker:
    def __init__(self):
        self.base_dir = os.path.join(current_app.instance_path, "cache", "tasks")
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_path(self, task_id: str) -> str:
        return os.path.join(self.base_dir, f"{task_id}.json")

    def create_task(self, source_name: str, params: dict) -> str:
        task_id = str(uuid.uuid4())
        data = {
            "task_id": task_id,
            "source_name": source_name,
            "status": "pending",
            "params": params,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "result": None,
            "error": None
        }
        self._write(task_id, data)
        return task_id

    def update_status(self, task_id: str, status: str, result=None, error=None):
        data = self.get_task(task_id)
        if data:
            data["status"] = status
            data["updated_at"] = datetime.utcnow().isoformat()
            if result is not None:
                data["result"] = result
            if error is not None:
                data["error"] = error
            self._write(task_id, data)

    def get_task(self, task_id: str) -> dict:
        path = self._get_path(task_id)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    def _write(self, task_id: str, data: dict):
        path = self._get_path(task_id)
        # Write to temporary file then rename for atomic write
        temp_path = path + ".tmp"
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(temp_path, path)
        except Exception:
            pass
