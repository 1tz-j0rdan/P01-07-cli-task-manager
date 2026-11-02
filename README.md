# P01-07 — CLI Task Manager

A Python command-line task manager with persistent JSON storage, CRUD operations, priorities, due dates, filtering, and automated tests.

## Requirements

Python 3.10+; no runtime third-party dependencies.

## Installation (Windows PowerShell)

```powershell
py -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Quick start

By default, the database is `tasks.json` in the current directory. That file is ignored by Git.

```powershell
python -m task_manager add "Finish portfolio project" --priority high --due 2026-11-10
python -m task_manager add "Write README" --priority medium
python -m task_manager list
python -m task_manager show 1
python -m task_manager edit 1 --title "Finish and publish portfolio project"
python -m task_manager done 1
python -m task_manager list --status done
python -m task_manager reopen 1
python -m task_manager delete 2
```

## Commands

| Command | Purpose |
| --- | --- |
| `add "TITLE" [--priority low\|medium\|high] [--due YYYY-MM-DD]` | Create task |
| `list [--status all\|pending\|done] [--priority all\|low\|medium\|high]` | List/filter |
| `list [--due-before YYYY-MM-DD] [--search TEXT] [--json]` | Filter by deadline/title; JSON output |
| `show ID` | Display a task |
| `edit ID [--title TITLE] [--priority ...] [--due DATE] [--clear-due]` | Modify task |
| `done ID` / `reopen ID` | Change completion status |
| `delete ID` | Remove task |

Use `--db PATH` **before** the command to select a database:

```powershell
python -m task_manager --db .\demo-files\my-tasks.json add "Sample task"
python -m task_manager --db .\demo-files\my-tasks.json list
```

Alternatively, set `TASK_MANAGER_DB` to a database path. `task-manager` is also installed as a console command.

## Data and design

- Human-readable JSON database with monotonically increasing task IDs.
- Each task stores `id`, `title`, `priority`, `due` (optional ISO date), and `status`.
- Atomic file replacement reduces the risk of partially written files.
- Clear error messages for invalid dates, missing task IDs, and corrupt databases.
- Designed for a **single local process at a time**. Concurrent writers are not supported.
- Dates are stored as strings; no timezone handling or reminders.

## Tests and lint

```powershell
python -m pytest -v
python -m ruff check .
```

GitHub Actions runs both checks on every push and pull request.

## Suggested extensions

Add tags, sorting by due date, export to CSV, task archiving, and file locking for multi-process use.
