from taskai.json_dir_database import JsonDirectoryDatabase
from taskai.views import view_lists, view_item
import os, shutil
from datetime import datetime

db = None
ids = {}
def _setup_db():
    global db
    db = JsonDirectoryDatabase(
        "_tmp_database_dir",
        "test_user",
        # debug=True
    )

def _cleanup_db():
    if os.path.exists("_tmp_database_dir"):
        shutil.rmtree("_tmp_database_dir")


def _populate_db():
    db.connect()
    root1 = db.create_item(name="root 1")
    child1 = db.create_item(name="child 1", parent_id=root1, priority=3)
    root2 = db.create_item(name="root 2", description="Describe Marcellus Wallace")
    child2 = db.create_item(name="child 2", parent_id=root2, priority=2)
    child3 = db.create_item(name="child 3", parent_id=root2, due_by=datetime(2026,10, 1))
    gchild1 = db.create_item(name="grandchild 1", parent_id=child3, completed=True, description="Say 'what' again.")
    db.create_comment("I dare you", item_id=gchild1)
    db.create_comment("I double dare you mothafucka, say 'what' one more goddamn time", item_id=gchild1)

    global ids
    ids.update(locals())

def test_view_lists():
    print("Root 1");print("-"*30)
    view_lists(db, [ids["root1"]])
    print("\n\n\n");print("Root 1");print("-"*30)
    view_lists(db, [ids["root2"]])

def test_view_item():
    print("\n\n\n");print("Grandchild");print("-"*30)
    view_item(db, ids["gchild1"])
    print("\n\n\n");print("Grandchild");print("-"*30)
    view_item(db, ids["root2"]) # should show sublist

if __name__ == "__main__":
    _cleanup_db()
    _setup_db()
    _populate_db()
    try:
        test_view_lists()
        test_view_item()
    except Exception as e:
        raise e
    finally:
    # import rich
    # import orjson as json
    # rich.print_json(json.dumps(_test_db.user_data).decode())
        _cleanup_db()