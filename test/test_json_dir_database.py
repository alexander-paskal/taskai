import sys, os; sys.path.append(os.getcwd());print(sys.path)
from todolist.json_dir_database import JsonDirectoryDatabase
from todolist.models import TodoList, TodoItem, Comment
import shutil


_test_db = None
def _setup_db():
    global _test_db
    _test_db = JsonDirectoryDatabase(
        "_tmp_database_dir",
        "test_user"
    )

def _cleanup_db():
    if os.path.exists("_tmp_database_dir"):
        shutil.rmtree("_tmp_database_dir")



def test_init():
    _setup_db()
    _test_db.connect()
    _test_db.commit()
    assert os.path.exists("_tmp_database_dir/test_user.json")


def test_create():


    for i in range(3):

        list = TodoList(name=f"list {i}")

        list_id = _test_db.create(list)
        for j in range(10):
            item = TodoItem(title=f"task {i}.{j}", list_id=list_id)
            item_id = _test_db.create(item)
            for k in range(2):
                comment = Comment(content=f"Comment {k}", item_id=item_id)
                _test_db.create(comment)
    
    _test_db.commit()
    assert len(_test_db.user_data[Comment.__name__]) == 3*10*2, "wrong number comments"
    user_data = _test_db.user_data
    ids = set(
        [k for k in user_data[Comment.__name__]] + 
        [k for k in user_data[TodoItem.__name__]] +
        [k for k in user_data[TodoList.__name__]]
    )
    assert len(ids) == 3+3*10+3*10*2, "not enough unique ids"

def test_delete():
    
    for i in range(1, 90, 10):
        _test_db.delete(i)
    
    user_data = _test_db.user_data
    ids = set(
        [k for k in user_data[Comment.__name__]] + 
        [k for k in user_data[TodoItem.__name__]] +
        [k for k in user_data[TodoList.__name__]]
    )
    try:
        _test_db.read(21)
        assert False, "should be runtime error here"
    except RuntimeError:
        pass
    assert len(ids) == 3+3*10+3*10*2 - 9, "wrong number unique ids"

if __name__ == "__main__":
    _cleanup_db()
    _setup_db()
    test_init()
    test_create()
    test_delete()
    # import rich
    # import orjson as json
    # rich.print_json(json.dumps(_test_db.user_data).decode())
    _cleanup_db()