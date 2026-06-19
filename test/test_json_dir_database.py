import sys, os; sys.path.append(os.getcwd());print(sys.path)
from taskai.json_dir_database import JsonDirectoryDatabase, DatabaseError
from taskai.models import TodoItem, Comment
import shutil


db = None
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



def test_init():
    _setup_db()
    db.connect()
    db.commit()
    assert os.path.exists("_tmp_database_dir/test_user.json")

def test_basic():
    db.connect()
    root1 = db.create_item(name="root 1")
    child1 = db.create_item(name="child 1", parent_id=root1)
    root2 = db.create_item(name="root 2")
    child2 = db.create_item(name="child 2", parent_id=root2)
    child3 = db.create_item(name="child 3", parent_id=root2)
    gchld1 = db.create_item(name="grandchild 1", parent_id=child3)
    print("After Creation")
    db._debug_print_tree()

    print("After deleting root")
    db.delete_item(root2)
    db._debug_print_tree()
    
    print("Modify")
    db.update_item(child1, name="el caballo loco")
    db._debug_print_tree()

    # verify errors work as expected
    try:
        db.get_item(root2)
        assert False, "this should error"
    except DatabaseError:
        pass
    try:
        db.get_item(gchld1)
        assert False, "this should error"
    except DatabaseError:
        pass



if __name__ == "__main__":
    _cleanup_db()
    _setup_db()
    try:
        test_init()
        test_basic()
    except Exception as e:
        raise e
    finally:
    # import rich
    # import orjson as json
    # rich.print_json(json.dumps(_test_db.user_data).decode())
        _cleanup_db()