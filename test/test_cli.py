from taskai.json_dir_database import JsonDirectoryDatabase
from taskai.cli import _parse_arg_string
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


CHAIN_TESTING_DIR = os.path.join(CWD, "_testing_chain_dir")

# smoke test for the chain command dispatch (execute_commands' case
# statements) - the DB-layer correctness (pointer-juggling, edge cases) is
# covered in detail by test_chains.py; this just confirms each command
# actually reaches its Controller method and doesn't blow up end to end
CHAIN_COMMANDS = [
    "task create \"P\"",
    "task add P \"H1\"",
    "task next H1 \"A1\"",          # chain: H1 -> A1
    "task add P \"H2\"",
    "task chain H2 A1",             # splice A1 (already mid-chain) into a new chain after H2
    "task show all",
    "task unchain A1",              # A1 leaves the chain, becomes a plain child of P again
    "task show all",
    "task create \"ChainDeleteTest\"",
    "task add ChainDeleteTest \"CH\"",
    "task next CH \"CA\"",
    "task next CA \"CB\"",
    "task delete CH -chain",        # deletes CH/CA/CB in one shot
    "task show all",
]


def test_run_chain_commands():

    if os.path.exists(CHAIN_TESTING_DIR):
        shutil.rmtree(CHAIN_TESTING_DIR)

    os.makedirs(CHAIN_TESTING_DIR, exist_ok=True)
    os.chdir(CHAIN_TESTING_DIR)

    try:
        for c in CHAIN_COMMANDS:
            print(f"executing command '{c}'")
            return_code = os.system(c)
            print(f"return code: {return_code}")
            if return_code != 0:
                raise RuntimeError("test failed with return code {}".format(return_code))
    finally:
        os.chdir(CWD)
        if os.path.exists(CHAIN_TESTING_DIR):
            shutil.rmtree(CHAIN_TESTING_DIR)

def test_args_parser():
    
    def _assert_list_equal(l1, l2):
        assert len(l1) == len(l2), f"{l1} length not equal to {l2} length"
        assert all([thing1==thing2 for thing1, thing2 in zip(l1, l2)]), f"{l1} not equal to {l2}"
    
    dataset = [
        ("show thing 1", ["show", "thing", "1"]),
        ("show 'this is a string' 2", ["show", "this is a string", "2"]),
        ("show https://url.com/thing?arg=1 hello there", ["show", "https://url.com/thing?arg=1", "hello", "there"])
    ]

    for input, label in dataset:
        output = _parse_arg_string(input)
        _assert_list_equal(label, output)

    

def _cleanup_db():
    os.chdir(CWD)
    if os.path.exists(TESTING_DIR):
        shutil.rmtree(TESTING_DIR)

if __name__ == "__main__":
    test_args_parser()
    # test_run_commands()
