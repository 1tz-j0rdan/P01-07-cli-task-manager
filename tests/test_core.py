import json

import pytest

from task_manager.cli import main
from task_manager.core import (
    TaskError,
    add,
    get,
    list_tasks,
    load,
    parse_due,
    remove,
    save,
    set_status,
    update,
)


@pytest.fixture
def data():
    return {"next_id": 1, "tasks": []}


def test_empty_load(tmp_path):
    assert load(tmp_path / "missing.json") == {"next_id": 1, "tasks": []}


def test_add(data):
    task = add(data, "  Write tests ", "high", "2026-12-01")
    assert task == {
        "id": 1, "title": "Write tests", "priority": "high",
        "due": "2026-12-01", "status": "pending",
    }
    assert data["next_id"] == 2


@pytest.mark.parametrize("title", ["", "   "])
def test_invalid_title(data, title):
    with pytest.raises(TaskError):
        add(data, title)


def test_invalid_priority(data):
    with pytest.raises(TaskError):
        add(data, "Test", "urgent")


@pytest.mark.parametrize("value", ["2026-02-30", "tomorrow", "2026/12/01", ""])
def test_invalid_date(value):
    with pytest.raises(TaskError):
        parse_due(value)


def test_no_due():
    assert parse_due(None) is None


def test_get(data):
    add(data, "One")
    assert get(data, 1)["title"] == "One"


def test_missing_id(data):
    with pytest.raises(TaskError):
        get(data, 123)


def test_update(data):
    add(data, "One")
    task = update(data, 1, title="Two", priority="low", due="2026-11-30")
    assert (task["title"], task["priority"], task["due"]) == (
        "Two", "low", "2026-11-30"
    )


def test_clear_due(data):
    add(data, "One", due="2026-11-30")
    assert update(data, 1, clear_due=True)["due"] is None


def test_invalid_update_title(data):
    add(data, "One")
    with pytest.raises(TaskError):
        update(data, 1, title=" ")


def test_invalid_update_priority(data):
    add(data, "One")
    with pytest.raises(TaskError):
        update(data, 1, priority="critical")


def test_complete_and_reopen(data):
    add(data, "One")
    assert set_status(data, 1, "done")["status"] == "done"
    assert set_status(data, 1, "pending")["status"] == "pending"


def test_invalid_status(data):
    add(data, "One")
    with pytest.raises(TaskError):
        set_status(data, 1, "blocked")


def test_delete_preserves_next_id(data):
    add(data, "One")
    remove(data, 1)
    assert add(data, "Two")["id"] == 2


def test_list_filters(data):
    add(data, "Fix server", "high", "2026-11-03")
    add(data, "Write docs", "low", "2026-12-01")
    add(data, "Fix tests", "high")
    set_status(data, 2, "done")
    assert [t["id"] for t in list_tasks(data, priority="high")] == [1, 3]
    assert [t["id"] for t in list_tasks(data, status="done")] == [2]
    assert [t["id"] for t in list_tasks(data, due_before="2026-11-10")] == [1]
    assert [t["id"] for t in list_tasks(data, search="FIX")] == [1, 3]


def test_invalid_filters(data):
    with pytest.raises(TaskError):
        list_tasks(data, status="blocked")
    with pytest.raises(TaskError):
        list_tasks(data, priority="critical")


def test_roundtrip(tmp_path, data):
    add(data, "Backup files", "high")
    path = tmp_path / "nested" / "tasks.json"
    save(path, data)
    assert load(path) == data


def test_corrupt_json(tmp_path):
    path = tmp_path / "tasks.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(TaskError):
        load(path)


@pytest.mark.parametrize("bad", [[], {}, {"next_id": 0, "tasks": []}])
def test_bad_database(tmp_path, bad):
    path = tmp_path / "tasks.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(TaskError):
        load(path)


def test_duplicate_ids(tmp_path, data):
    add(data, "One")
    data["tasks"].append(dict(data["tasks"][0]))
    path = tmp_path / "tasks.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(TaskError):
        load(path)


def test_invalid_next_id(tmp_path, data):
    add(data, "One")
    data["next_id"] = 1
    path = tmp_path / "tasks.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(TaskError):
        load(path)


def test_cli_workflow(tmp_path, capsys):
    db = str(tmp_path / "tasks.json")
    assert main(["--db", db, "add", "Ship project", "--priority", "high"]) == 0
    assert main(["--db", db, "list"]) == 0
    assert "Ship project" in capsys.readouterr().out
    assert main(["--db", db, "done", "1"]) == 0
    assert main(["--db", db, "show", "1"]) == 0
    assert '"status": "done"' in capsys.readouterr().out
    assert main(["--db", db, "reopen", "1"]) == 0
    assert main(["--db", db, "edit", "1", "--title", "Ship v1"]) == 0
    assert main(["--db", db, "delete", "1"]) == 0
    assert load(db)["tasks"] == []


def test_cli_json_filter(tmp_path, capsys):
    db = str(tmp_path / "tasks.json")
    main(["--db", db, "add", "First"])
    capsys.readouterr()
    assert main(["--db", db, "list", "--json", "--status", "pending"]) == 0
    assert json.loads(capsys.readouterr().out)[0]["title"] == "First"


def test_cli_missing_task(tmp_path, capsys):
    assert main(["--db", str(tmp_path / "db.json"), "done", "999"]) == 1
    assert "not found" in capsys.readouterr().err


def test_cli_invalid_due(tmp_path, capsys):
    assert main(["--db", str(tmp_path / "db.json"), "add", "Test", "--due", "no"]) == 1
    assert "YYYY-MM-DD" in capsys.readouterr().err


def test_cli_conflicting_due(tmp_path, capsys):
    db = str(tmp_path / "db.json")
    main(["--db", db, "add", "Test"])
    assert main(["--db", db, "edit", "1", "--due", "2026-11-03", "--clear-due"]) == 1
    assert "either" in capsys.readouterr().err
