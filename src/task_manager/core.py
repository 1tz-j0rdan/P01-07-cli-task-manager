"""Task validation, persistence, and CRUD operations."""

import json
import os
import tempfile
from datetime import date
from pathlib import Path

PRIORITIES = ("low", "medium", "high")
STATUSES = ("pending", "done")


class TaskError(ValueError):
    """A user-correctable task manager error."""


def parse_due(value):
    if value is None:
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except (TypeError, ValueError) as exc:
        raise TaskError("Due date must be YYYY-MM-DD") from exc


def load(path):
    path = Path(path)
    if not path.exists():
        return {"next_id": 1, "tasks": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TaskError(f"Unable to read task database: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("tasks"), list):
        raise TaskError("Invalid task database structure")
    if type(data.get("next_id")) is not int or data["next_id"] < 1:
        raise TaskError("Invalid next task ID")
    seen = set()
    for task in data["tasks"]:
        if not isinstance(task, dict) or type(task.get("id")) is not int:
            raise TaskError("Invalid task record")
        if task["id"] < 1 or task["id"] in seen:
            raise TaskError("Duplicate or invalid task ID")
        seen.add(task["id"])
        if not isinstance(task.get("title"), str) or not task["title"].strip():
            raise TaskError("Invalid task title")
        if task.get("priority") not in PRIORITIES or task.get("status") not in STATUSES:
            raise TaskError("Invalid task priority or status")
        if task.get("due") is not None:
            parse_due(task["due"])
    if seen and data["next_id"] <= max(seen):
        raise TaskError("Invalid next task ID")
    return data


def save(path, data):
    """Atomically replace the JSON database on the same filesystem."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False
        ) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def add(data, title, priority="medium", due=None):
    title = title.strip()
    if not title:
        raise TaskError("Task title cannot be empty")
    if priority not in PRIORITIES:
        raise TaskError("Invalid priority")
    task = {
        "id": data["next_id"], "title": title, "priority": priority,
        "due": parse_due(due), "status": "pending",
    }
    data["tasks"].append(task)
    data["next_id"] += 1
    return task


def get(data, task_id):
    for task in data["tasks"]:
        if task["id"] == task_id:
            return task
    raise TaskError(f"Task #{task_id} not found")


def update(data, task_id, title=None, priority=None, due=None, clear_due=False):
    task = get(data, task_id)
    if title is not None:
        if not title.strip():
            raise TaskError("Task title cannot be empty")
        task["title"] = title.strip()
    if priority is not None:
        if priority not in PRIORITIES:
            raise TaskError("Invalid priority")
        task["priority"] = priority
    if due is not None:
        task["due"] = parse_due(due)
    if clear_due:
        task["due"] = None
    return task


def set_status(data, task_id, status):
    if status not in STATUSES:
        raise TaskError("Invalid status")
    task = get(data, task_id)
    task["status"] = status
    return task


def remove(data, task_id):
    task = get(data, task_id)
    data["tasks"].remove(task)
    return task


def list_tasks(data, status="all", priority="all", due_before=None, search=None):
    if status != "all" and status not in STATUSES:
        raise TaskError("Invalid status filter")
    if priority != "all" and priority not in PRIORITIES:
        raise TaskError("Invalid priority filter")
    cutoff = parse_due(due_before)
    tasks = data["tasks"]
    return sorted(
        (
            task for task in tasks
            if (status == "all" or task["status"] == status)
            and (priority == "all" or task["priority"] == priority)
            and (cutoff is None or (task["due"] is not None and task["due"] <= cutoff))
            and (not search or search.casefold() in task["title"].casefold())
        ),
        key=lambda task: task["id"],
    )
