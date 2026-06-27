# standard lib
import argparse
import os
from datetime import datetime
import builtins
import fnmatch
import sys
import subprocess
import getpass

# local
from taskai.json_dir_database import JsonDirectoryDatabase
from taskai.views import view_lists, view_item, view_items
from taskai.models import TodoItem, Comment
from taskai.services.ai import ai_headstart_service, ai_natural_language_service
from taskai.services.user_setup import user_setup_service
from taskai.services.repair_database import repair_database_service
from taskai.help_menu import help_menu
from taskai.config import GlobalConfig

# external
from rich import print, print_json
from rich.console import Console
import rich
from rich.prompt import Prompt

# config
DB_PATH = ".taskai/task_db"
USER = os.getenv("USER") if sys.platform == "linux" else os.getenv('USERNAME')
db = JsonDirectoryDatabase(
        DB_PATH,
        USER,
)
db.connect()
GlobalConfig.load_dict(db.get_config())

class Controller:

    # utilities
    def _find_model_by_stringmatch(attr: str, pattern: str) -> TodoItem|Comment|None:

        for record_type in [
            TodoItem,
            Comment
        ]:
            batch_attrs = db.get_item_batch_attr(attr)
            inside_out = {v: k for k, v in batch_attrs.items()}  # TODO this is hacky
            results = fnmatch.filter(batch_attrs.values(), pattern)
            if results:
                id_ = inside_out[results[0]]  # might be duplication
                return db.get_item(id_)
        return None

    def _parse_item_kwargs(kwargs):
        for k, v in kwargs.copy().items():
            if v is None:
                continue
            match k:
                case "completed": kwargs["completed"] = bool(v)
                case "due_by": kwargs["due_by"] = datetime.strptime(v, "%m-%d-%Y")
                case "depends_on": kwargs["dependency_ids"] = v.split(",")
        return kwargs

    def _get_root_ids():
        return [
            item_id for item_id in db.get_item_ids()
            if db.get_item_attr(item_id, "parent_id") is None
        ]

    def _debug(args, kwargs):
        print("args:", args)
        print("kwargs:", kwargs)

    # CRUD
    def show_all(show_done=True):
        view_lists(db, Controller._get_root_ids(), show_done=show_done)

    def show_by_item_name(value: str, show_done=True):
        model = Controller._find_model_by_stringmatch("name", value)
        if model:
            Controller.show_item(model.id, show_done=show_done)
        else:
            print(f"Could not find item matching pattern '{value}'")
    
    def show_item(item_id: int, **kwargs):
        view_item(db, item_id, **kwargs)

    def show_items(item_ids: str, **kwargs):
        item_ids = item_ids.split(",")
        view_items(db, item_ids, **kwargs)
    
    def show_examples():
        ...
        print("Not implemented yet")

    def create_item(name: str, parent_id=None, **kwargs):
        if parent_id is not None and not _is_int(parent_id):
            parent = Controller._find_model_by_stringmatch("name", parent_id)
            if not parent:
                Controller.throw_error(f"Could not find parent by id '{parent_id}'")
                return
            parent_id = parent.id

        kwargs = Controller._parse_item_kwargs(kwargs)
        item_id = db.create_item(name=name, parent_id=parent_id, **kwargs)
        print(f"Created item {item_id} - '{name}'")
        db.commit()

    def create_comment(item_id: int|str, content: str):
        comment_id = db.create_comment(content=content, item_id=item_id)
        print(f"Added comment {comment_id} to item {item_id} - '{content}'")
        db.commit()
            
    def update_item(item_id: int|str, **kwargs):
        if not _is_int(item_id):
            item_id = Controller._find_model_by_stringmatch("name", item_id)
        db.update_item(item_id, **kwargs)
        print(f"Updated item {item_id}")
        db.commit()

    def delete_item(id_: int|str):
        db.delete_item(id_)
        db.commit()
        print(f"Deleted item {id_}")
    
    def delete_item_by_name(name: str):
        item = Controller._find_model_by_stringmatch("name", name)
        if item:
            db.delete_item(item.id)
            db.commit()
        else:
            Controller.throw_error("Cannot find list by name")
    
    def delete_completed():
        for item_id in db.get_item_ids():
            item: TodoItem = db.get_item(item_id)
            if item.completed:
                db.delete_item(item_id)
        db.commit()
    
    def ai_headstart(item_id: int|str):
        ai_response_text = ai_headstart_service(db, item_id)
        comment_content = f"AI: {ai_response_text}"
        Controller.create_comment(item_id, comment_content)
        print(comment_content)

    def ai_natural_language(prompt: str):
        ai_natural_language_service(db, prompt)
    
    def throw_error(error_description: str, *args, **kwargs):
        print(f"[red]ERROR: {error_description}[/red]\nargs={args}\nkwargs={kwargs}")
        import sys
        sys.exit(-1)
    
    def get_config_value(key: str):
        print(getattr(db.get_config(), key))
    
    def list_config():
        for k, v in db.get_config().model_dump().items():
            print(f"{k}={v}")
    
    def set_config_value(key: str, value: any):
        db.update_config(**{key: value})
        db.commit()
        print(f"setting {key}={value}")
    
    def remove_config_value(key: str):
        db.update_config(**{key: None})
        db.commit()
    
    def run_setup_service():
        user_setup_service(db)

    def repair_service():
        repair_database_service(db)

    def move_item(item_id: int|str, parent_identifier: int|str):
        
        if _is_int(item_id):
            item = db.get_item(item_id)
        else:
            item = Controller._find_model_by_stringmatch("name", item_id)
        
        # remove from old parent
        if item.parent_id is not None:
            db.remove_child_from_parent(item.id, item.parent_id)
        
        # add to new parent
        if _is_int(parent_identifier):
            new_parent_id = parent_identifier
        elif not parent_identifier:  # anything evaluating to false
            new_parent_id=None
        else:
            new_parent_id = Controller._find_model_by_stringmatch("name", parent_identifier).id
        
        db.update_item(item.id, parent_id=new_parent_id)
        if new_parent_id is not None:
            db.add_child_to_parent(item.id, new_parent_id)

        
        db.commit()     
    
    def add_dependency(src_id: int|str, dst_id: int|str):
        """Adds a depedency src -> dst, meaning src depends on dst"""
        dependency_ids = db.get_item_attr(src_id, "dependency_ids")
        dependency_ids.append(dst_id)
        db.update_item(src_id, dependency_ids=dependency_ids)
        db.commit()

# utilities
def _parse_remaining(remaining_args: list[str]) -> tuple[list, dict]:

    for i, _arg in enumerate(remaining_args):
        remaining_args[i] = _arg.replace(" ", "+-*/")
    remaining_args = " ".join(remaining_args).replace("="," ").split(" ")
    for i, _arg in enumerate(remaining_args):
        remaining_args[i] = _arg.replace("+-*/", " ")
    
    # outputs
    args = []
    kwargs = {}

    while remaining_args:
        next_arg = remaining_args.pop(0)
        if next_arg.startswith("--"):
            assert remaining_args, "kwarg specified with no value provided"
            kwargs[next_arg[2:]] = remaining_args.pop(0)
        else:
            args.append(next_arg)


    return args, kwargs

def _is_int(val: any) -> bool:
    try:
        int(val)
        return True
    except:
        return False

def _clear_screen():
    if sys.platform == "linux":
        os.system("clear")
    elif sys.platform == "windows":
        os.system("cls")
    else:
        os.system("clear")

def execute_commands(*args, **kwargs) -> int:
    """
    Return codes:
        0 -> termination
        1 -> continue
    """
    try:
        match args[0]:
            case "help":
                print(help_menu['general'])

            case "setup":
                Controller.run_setup_service()

            case "show":
                match args[1]:
                    case "all": Controller.show_all(*args[2:], **kwargs)
                    case "examples": Controller.show_examples()
                    case _ if _is_int(args[1]): Controller.show_item(*args[1:], **kwargs)
                    case _: Controller.show_by_item_name(args[1], **kwargs)

            case "create":
                Controller.create_item(args[1], **kwargs)
            
            case "update":
                Controller.update_item(args[1], **kwargs)
                
            case "delete" | "remove":
                match args[1]:
                    case _ if _is_int(args[1]): Controller.delete_item(args[1])
                    case "completed" | "done": Controller.delete_completed()
                    case _: Controller.delete_item_by_name(args[1])

            case "comment":
                match args[1]:
                    case _ if _is_int(args[1]): Controller.create_comment(*args[1:], **kwargs)
            
            case "config":
                match args[1]:
                    case "set": Controller.set_config_value(key=args[2], value=args[3])
                    case "get": Controller.get_config_value(key=args[2])
                    case "list"|"show": Controller.list_config()
                    case "pop": Controller.remove_config_value(key=args[2])
                    case _: Controller.throw_error("unrecognized command", *args, **kwargs)
            
            case "ai":
                match args[1]:
                    case "headstart": Controller.ai_headstart(*args[2:], **kwargs)
                    case _: Controller.ai_natural_language(" ".join(args[1:]))

            case "nuke":
                db.remove()
            
            case "add":
                parent_identifier = args[1]
                item_name = args[2]
                Controller.create_item(item_name, parent_identifier, **kwargs)

            case "complete" | "done":
                match args[1]:
                    case _ if _is_int(args[1]): Controller.update_item(args[1], completed=True)
                    case _: Controller.throw_error("unrecognized complete command", *args, **kwargs)

            case "examples":
                Controller.show_examples()

            case "repair":
                Controller.repair_service()

            case "clear":
                Controller.delete_completed()

            case "move":
                Controller.move_item(args[1], args[2])
                
            case "depend":
                src_id, dst_id = args[1:3]
                match (src_id, dst_id):
                    case _ if _is_int(src_id) and _is_int(dst_id): Controller.add_dependency(src_id, dst_id) 
                    case _: Controller.throw_error("Invalid arrow argument, must be one of (->, <-)")
            
            # developer use
            case "db":
                import orjson as json
                print_json(json.dumps(db.read(args[1]).model_dump()).decode())

            case "exit" | "exit()" | "quit":
                return 0

            case _: Controller.throw_error("unrecognized command", *args, **kwargs)


    except Exception as e: 
        raise e
        Controller.throw_error(f"encountered exception '{e}'", *args, **kwargs)

    return 1


def interactive_program():
    # console = Console()
    # builtins.print = console.print

    response = ""
    last_show_command = None
    args = None
    kwargs = None

    # TODO save the last show

    _clear_screen()
    while True:

        try:

            # render last show command
            if last_show_command is not None:
                execute_commands(*last_show_command[0], **last_show_command[1])

            Console().rule()
            
            # prompt user input
            response = Prompt.ask("Type your commands:", default=response)
            
            # parse commands
            args, kwargs = _parse_remaining(response.split(" "))
            if args[0] == "task":
                args = args[1:]

            # defer show
            if args[0] == "show":
                last_show_command = (args, kwargs)
                return_code = 1
            else:
                return_code = execute_commands(*args, **kwargs)
            
            _clear_screen()
            if return_code == 0:
                break
            
        except KeyboardInterrupt:
           break
        except Exception as e:
            print(e)
        
    _clear_screen()
    sys.exit(1)


def entry_point():
    arg_parser = argparse.ArgumentParser()
    _, argv = arg_parser.parse_known_args()


    if not argv:
        interactive_program()

    if argv[0] in ("help","--help"):
        print(help_menu["general"])
        return

    args, kwargs = _parse_remaining(argv)

    execute_commands(*args, **kwargs)


if __name__ == "__main__":
    entry_point()
