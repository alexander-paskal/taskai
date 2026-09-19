import sys, os; sys.path.append(os.getcwd())
import shutil

import orjson as json

from taskai.json_dir_database import JsonDirectoryDatabase

LEGACY_DIR = "_tmp_legacy_dir"


def _write_legacy_file(items: dict, config: dict | None = None):
    os.makedirs(LEGACY_DIR, exist_ok=True)
    data = {"name": "test_user", "id_counter": len(items), "todo_items": items, "config": config or {}}
    with open(os.path.join(LEGACY_DIR, "test_user.json"), "wb") as f:
        f.write(json.dumps(data))


def _connect() -> JsonDirectoryDatabase:
    db = JsonDirectoryDatabase(LEGACY_DIR, "test_user")
    db.connect()
    return db


def _cleanup():
    if os.path.exists(LEGACY_DIR):
        shutil.rmtree(LEGACY_DIR)


def test_due_by_is_read_as_due():
    _cleanup()
    try:
        _write_legacy_file({
            "1": {"id": 1, "name": "old", "due_by": "2026-10-01T00:00:00"},
            "2": {"id": 2, "name": "no due", "due_by": None},
            "3": {"id": 3, "name": "both", "due_by": "2026-01-01T00:00:00", "due": "2026-02-02T00:00:00"},
        })
        db = _connect()

        assert db.get_item(1).due.isoformat() == "2026-10-01T00:00:00"
        assert db.get_item(2).due is None
        # `due` wins when both are set - the legacy key never overwrites it
        assert db.get_item(3).due.isoformat() == "2026-02-02T00:00:00"

        # raw-dict reads see the new name too, and the legacy key is gone
        assert db.get_item_attr(1, "due") == "2026-10-01T00:00:00"
        assert all("due_by" not in item for item in db.user_data.todo_items.values())
    finally:
        _cleanup()


def test_migrated_data_is_written_back_under_the_new_name():
    _cleanup()
    try:
        _write_legacy_file({"1": {"id": 1, "name": "old", "due_by": "2026-10-01T00:00:00"}})
        db = _connect()
        db.commit()

        with open(os.path.join(LEGACY_DIR, "test_user.json"), "rb") as f:
            saved = json.loads(f.read())
        assert "due_by" not in saved["todo_items"]["1"]
        assert saved["todo_items"]["1"]["due"] == "2026-10-01T00:00:00"
    finally:
        _cleanup()


def test_saved_display_string_is_migrated():
    _cleanup()
    try:
        _write_legacy_file({}, config={"DISPLAY_STRING": "id name status due_by"})
        db = _connect()
        assert db.get_config().DISPLAY_STRING == "id name status due"
    finally:
        _cleanup()
