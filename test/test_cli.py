from taskai.json_dir_database import JsonDirectoryDatabase
import os
import shutil


CWD = os.path.abspath(os.getcwd())
TESTING_DIR = os.path.join(CWD, "_testing_dir")

db = None
ids = {}
def _setup_db():
    global db
    
    db = JsonDirectoryDatabase(
        "_tmp_database_dir",
        "test_user",
        # debug=True
    )

COMMANDS = [
    "task create \"test item 1\"",
    "task show all",
    "task add test* \"subitem 2\"",
    "task show all",
    "task show subitem*",
    "task delete subitem*",
    "task show all",
    "task create \"test item 2\"",
    "task add \"*item 2\" \"subitem2\"",
    "task show all",
    "task move subitem2 \"*item 1\"",
    "task show all"
]


def test_run_commands():

    _cleanup_db()

    os.makedirs(TESTING_DIR, exist_ok=True)
    os.chdir(TESTING_DIR)

    _setup_db()
    try:
        for c in COMMANDS:
            print(f"executing command '{c}'")
            return_code = os.system(c)
            print(f"return code: {return_code}")
            if return_code != 0:
                raise RuntimeError("test failed with return code {}".format(return_code))
    except Exception as e:
        raise e
    finally:
        _cleanup_db()


def _cleanup_db():
    os.chdir(CWD)
    if os.path.exists(TESTING_DIR):
        shutil.rmtree(TESTING_DIR)

if __name__ == "__main__":

    test_run_commands()
