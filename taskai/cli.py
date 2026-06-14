# standard lib
import argparse
import os
from datetime import datetime
import builtins
import fnmatch

# local
from taskai.json_dir_database import JsonDirectoryDatabase
from taskai.views import view_lists, view_item, view_items
from taskai.models import Base, TodoItem, TodoList, Comment
from taskai.services.ai import ai_headstart_service, ai_natural_language_service
from taskai.services.user_setup import user_setup_service
from taskai.services.repair_database import repair_database_service
from taskai.help_menu import help_menu
from taskai.config import GlobalConfig

# external
from rich import print

# config
DB_PATH = ".taskai/task_db"
USER = os.getenv("USER")
db = JsonDirectoryDatabase(
        DB_PATH,
        USER
)
db.connect()

og_help = builtins.help
def new_help(*args, **kwargs):
    print(f"help: args: {args}, kwargs: {kwargs}")
    return og_help(*args, **kwargs)
builtins.help = new_help

class Controller:

    # utilities
    def _find_model_by_stringmatch(attr: str, pattern: str) -> TodoItem|TodoList|Comment|None:

        for record_type in [
            TodoList,
            TodoItem,
            Comment
        ]:
            batch_attrs = db.read_batch_attr(record_type, attr)
            inside_out = {v: k for k, v in batch_attrs.items()}  # TODO this is hacky
            results = fnmatch.filter(batch_attrs.values(), pattern)
            if results:
                id_ = inside_out[results[0]]  # might be duplication
                return db.read(id_)
                
        return None


    def _debug(args, kwargs):
        print("args:", args)
        print("kwargs:", kwargs)

    # CRUD
    def show_all(show_done=True):
        view_lists(db, db.lists, show_done=show_done)
    
    def show_by_id(id_, show_done=True):
        if id_ in db.items:
            Controller.show_item(id_)
        elif id_ in db.lists:
            Controller.show_list(id_, show_done=show_done)
    
    def show_by_list_name(value: str, show_done=True):
        model = Controller._find_model_by_stringmatch("name", value)
        if isinstance(model, TodoList):
            Controller.show_list(model.id, show_done=show_done)
        else:
            print(f"Could not find list with substring '{value}'")

    def show_list(list_id: int|str, show_done=True):
        view_lists(db, [list_id], show_done=show_done)
    
    def show_lists():
        view_lists(db, db.lists.keys(), show_items=False)
    
    def show_item(item_id: int|str):
        view_item(db, item_id)

    def show_items(item_ids: str):
        item_ids = item_ids.split(",")
        view_items(db, item_ids)
    
    def show_examples():
        ...
        print("Not implemented yet")

    def create_list(name: str):
        list = TodoList(name=name)
        list_id = db.create(list)
        db.commit()
        print(f"Creating list {list_id} - {list.name}")

    def create_item(list_id: int|str, title: str, **kwargs):
        try:
            int(list_id)
        except ValueError:
            list_ = Controller._find_model_by_stringmatch("name", list_id)
            # TODO this should be just lists, not models
            list_id = list_.id

        item = TodoItem(title=title, list_id=list_id)

        for k, v in kwargs.items():
            if v is None:
                continue
            match k:
                case "completed": item.completed = bool(v)
                case "description": item.description = str(v)
                case "due_by": item.due_by = datetime.strptime(v, "%Y-%m-%d")
                case "parent": item.parent = str(v)
                case "priority": item.priority = int(v)
                case "depends_on": item.dependency_ids.extend(v.split(","))
                # TODO handle recurrence
        db.create(item)
        db.commit()

    def create_comment(item_id: int|str, content: str):
        comment = Comment(
            item_id=item_id,
            content=content
        )
        db.create(comment)
        db.commit()
            
    def update_item(item_id: int|str, **kwargs):
        item: TodoItem = db.read(item_id)
        for k, v in kwargs.items():
            if v is None:
                continue
            match k:
                case "title": item.title = str(v)
                case "list_id": item.list_id = str(v)
                case "completed": item.completed = bool(v)
                case "description": item.description = str(v)
                case "due_by": item.due_by = datetime.strptime(v, "%Y-%m-%d")
                case "parent": item.parent = str(v)
                case "priority": item.priority = int(v)
                # TODO handle recurrence

        db.update(item)
        db.commit()

    def delete(id_: int|str):
        db.delete(id_)
        db.commit()
        print(f"Deleted {id_}")
    
    def delete_list_by_name(name: str):
        list_ = Controller._find_model_by_stringmatch("name", name)
        if list_:
            db.delete(list_.id)
            db.commit()
        else:
            Controller.throw_error("Cannot find list by name")

    
    def delete_completed():
        for item_id in db.items.copy():
            item: TodoItem = db.read(item_id)
            if item.completed:
                db.delete(item_id)
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
    
    def get_config_value(key: str):
        print(db.get_config_value(key))
    
    def list_config():
        for k, v in db.get_config().items():
            print(f"{k}={v}")
    
    def set_config_value(key: str, value: any):
        db.set_config_value(key, value)
        db.commit()
        print(f"setting {key}={value}")
    
    def remove_config_value(key: str):
        db.config.pop(key)
        db.commit()
    
    def run_setup_service():
        user_setup_service(db)

    def repair_service():
        repair_database_service(db)

    def move_item(item_id: int|str, list_identifier: int|str):

        if item_id not in db.items:
            Controller.throw_error(f"Couldn't find items with id {item_id}")
        item: TodoItem = db.read(item_id)
        
        if _is_int(list_identifier):
            new_list_: TodoList = db.read(list_identifier)
        else:
            new_list_: TodoList = Controller._find_model_by_stringmatch("name", list_identifier)
        if not new_list_:
            Controller.throw_error(f"Couldn't locate list by identifier {list_identifier}")
        
        # update item
        item.list_id = new_list_.id
        db.update(item)
        
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




def entry_point():

    arg_parser = argparse.ArgumentParser()
    _, argv = arg_parser.parse_known_args()


    if not argv:
        print(help_menu["general"])
        return

    if argv[0] in ("help","--help"):
        print(help_menu["general"])
        return

    args, kwargs = _parse_remaining(argv)
    GlobalConfig.load_dict(db.config)

    try:
        match args[0]:
            case "setup":
                Controller.run_setup_service()

            case "show":
                match args[1]:
                    case "all": Controller.show_all(*args[2:], **kwargs)
                    case "list": Controller.show_list(*args[2:], **kwargs)
                    case "lists": Controller.show_lists() 
                    case "item": Controller.show_item(*args[2:], **kwargs)
                    case "items": Controller.show_item(*args[2:], **kwargs)
                    case "examples": Controller.show_examples()
                    case _ if _is_int(args[1]): Controller.show_by_id(*args[1:], **kwargs)
                    case _: Controller.show_by_list_name(args[1], **kwargs)

            case "create":
                match args[1]:
                    case "item": Controller.create_item(*args[2:], **kwargs)
                    case "list": Controller.create_list(*args[2:], **kwargs)
                    case "comment": Controller.create_comment(*args[2:], **kwargs)
                    case _: Controller.throw_error("uncrecognized create command", *args, **kwargs)
            
            case "update":
                match args[1]:
                    case _ if _is_int(args[1]): Controller.update_item(args[1], **kwargs)
                    case _: Controller.throw_error("uncregnozed update command", *args, **kwargs)

            case "delete" | "remove":
                match args[1]:
                    case _ if _is_int(args[1]): Controller.delete(args[1])
                    case "item": Controller.delete(args[2])
                    case "list": Controller.delete(args[2])
                    case "completed" | "done": Controller.delete_completed()
                    case _: Controller.delete_list_by_name(args[1])

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
                Controller.create_item(*args[1:], **kwargs)

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
                match args[1]:
                    case _ if _is_int(args[1]): Controller.move_item(args[1], args[2])
                    case _: Controller.throw_error("Unrecognized arguments", *args, **kwargs)

            case _: Controller.throw_error("unrecognized command", *args, **kwargs)
    except Exception as e: 
        Controller.throw_error(f"encountered exception '{e}'", *args, **kwargs)



if __name__ == "__main__":
    entry_point()
