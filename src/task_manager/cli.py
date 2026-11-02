"""Command-line interface for the task manager."""

import argparse
import json
import os
import sys
from pathlib import Path

from task_manager.core import (
    PRIORITIES,
    TaskError,
    add,
    get,
    list_tasks,
    load,
    remove,
    save,
    set_status,
    update,
)


def parser():
    root = argparse.ArgumentParser(description="Persistent CLI task manager")
    root.add_argument(
        "--db", type=Path, default=Path(os.environ.get("TASK_MANAGER_DB", "tasks.json")),
        help="JSON database path (default: tasks.json)",
    )
    commands = root.add_subparsers(dest="command", required=True)
    create = commands.add_parser("add", help="Create a task")
    create.add_argument("title")
    create.add_argument("--priority", choices=PRIORITIES, default="medium")
    create.add_argument("--due", help="Due date YYYY-MM-DD")
    listing = commands.add_parser("list", help="List/filter tasks")
    listing.add_argument("--status", choices=("all", "pending", "done"), default="all")
    listing.add_argument("--priority", choices=("all", *PRIORITIES), default="all")
    listing.add_argument("--due-before", help="Include tasks due on or before YYYY-MM-DD")
    listing.add_argument("--search", help="Case-insensitive title search")
    listing.add_argument("--json", action="store_true", help="Machine-readable output")
    show = commands.add_parser("show", help="Show task details")
    show.add_argument("id", type=int)
    edit = commands.add_parser("edit", help="Edit a task")
    edit.add_argument("id", type=int)
    edit.add_argument("--title")
    edit.add_argument("--priority", choices=PRIORITIES)
    edit.add_argument("--due")
    edit.add_argument("--clear-due", action="store_true")
    for name in ("done", "reopen", "delete"):
        command = commands.add_parser(name, help=f"{name.capitalize()} a task")
        command.add_argument("id", type=int)
    return root


def format_task(task):
    due = task["due"] or "-"
    return (
        f"#{task['id']} [{task['status']}] [{task['priority']}] "
        f"due:{due} {task['title']}"
    )


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        data = load(args.db)
        changed = False
        if args.command == "add":
            task = add(data, args.title, args.priority, args.due)
            changed = True
            print(f"Added {format_task(task)}")
        elif args.command == "list":
            tasks = list_tasks(data, args.status, args.priority, args.due_before, args.search)
            if args.json:
                print(json.dumps(tasks, indent=2, ensure_ascii=False))
            else:
                for task in tasks:
                    print(format_task(task))
                print(f"{len(tasks)} task(s)")
        elif args.command == "show":
            print(json.dumps(get(data, args.id), indent=2, ensure_ascii=False))
        elif args.command == "edit":
            if args.due is not None and args.clear_due:
                raise TaskError("Use either --due or --clear-due")
            task = update(data, args.id, args.title, args.priority, args.due, args.clear_due)
            changed = True
            print(f"Updated {format_task(task)}")
        elif args.command in ("done", "reopen"):
            task = set_status(data, args.id, "done" if args.command == "done" else "pending")
            changed = True
            print(f"Updated {format_task(task)}")
        elif args.command == "delete":
            task = remove(data, args.id)
            changed = True
            print(f"Deleted #{task['id']}")
        if changed:
            save(args.db, data)
        return 0
    except (TaskError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
