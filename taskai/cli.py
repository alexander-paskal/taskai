# standard lib
import argparse
import os
import builtins
import fnmatch
import sys
import subprocess
import getpass

# local
from taskai.dates import parse_date_value
from taskai.json_dir_database import JsonDirectoryDatabase
from taskai.views import view_lists, view_item
from taskai.filters import (
    FilterError,
    looks_like_filters,
    match_items,
    parse_filters,
    with_ancestors,
)
from taskai.models import TodoItem, CLIConfig
from taskai.services.ai import ai_headstart_service, ai_natural_language_service
from taskai.services.user_setup import user_setup_service
from taskai.services.repair_database import repair_database_service
from taskai.services.pomodoro import pomodoro_service
from taskai.help_menu import help_menu
from taskai.config import GlobalConfig
from taskai.errors import TaskCLIError

# external
from rich import print, print_json
from rich.console import Console
import rich
from rich.prompt import Prompt, Confirm

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
    def _find_model_by_stringmatch(attr: str, pattern: str) -> TodoItem|None:
        batch_attrs = db.get_item_batch_attr(attr)
        matches = [
            id_ for id_, value in batch_attrs.items()
            if fnmatch.fnmatch(value, pattern)
        ]
        if len(matches) == 1:
            return db.get_item(matches[0])
        if len(matches) > 1:
            listing = "\n".join(
                f"    {m}: {batch_attrs[m]}" for m in matches
            )
            Controller.throw_error(
                f"'{pattern}' matches {len(matches)} items:\n{listing}\n"
                f"Please use a unique pattern or the item ID directly"
            )
        return None

    def _find_item_by_identifier(identifier: str|int) -> TodoItem:
        if _is_int(identifier):
            return db.get_item(identifier)
        else:
            return Controller._find_model_by_stringmatch("name", identifier)

    def _resolve_item(identifier: str|int) -> TodoItem:
        """Like _find_item_by_identifier, but a missing item is a hard error
        instead of None - use this in any command that needs an item to
        exist rather than re-checking for None at every call site."""
        item = Controller._find_item_by_identifier(identifier)
        if item is None:
            Controller.throw_error(f"Could not find item matching '{identifier}'")
        return item

    def _flatten_item_descendants(item: TodoItem, existing=None) -> list[int]:
        """DFS through children and chain links - a chain's non-head members
        are never in anyone's child_ids, they're only reachable by walking
        next_chain_id, so both have to be followed to reach everything."""
        if existing is None:
            existing = []

        existing.append(item.id)
        for child_id in item.child_ids:
            child = db.get_item(child_id)
            Controller._flatten_item_descendants(child, existing=existing)

        if item.next_chain_id is not None:
            next_item = db.get_item(item.next_chain_id)
            Controller._flatten_item_descendants(next_item, existing=existing)

        return existing


    def _parse_item_kwargs(kwargs):
        # idempotent: also called on the already-parsed kwargs that
        # update_item()'s recursive branch passes back down
        for k, v in kwargs.copy().items():
            if v is None:
                continue
            match k:
                case "completed":
                    # note: bool("false") is True — parse the string, don't
                    # cast it. Real bools (the recursive re-parse, and the
                    # complete/done/undone dispatch) pass straight through.
                    if isinstance(v, bool):
                        kwargs["completed"] = v
                    else:
                        kwargs["completed"] = str(v).strip().lower() in ("true", "1", "yes")
                case "due":
                    if isinstance(v, str):
                        kwargs["due"] = parse_date_value(v)
                case "depends_on":
                    # CLI-facing alias for the model's dependency_ids field;
                    # accepts a comma-separated id list ("1,2,3") or one id
                    kwargs["dependency_ids"] = [
                        int(x) for x in str(v).split(",") if str(x).strip()
                    ]
                    del kwargs["depends_on"]
        return kwargs

    def _get_root_ids():
        # a chain member's parent_id is always None too (only prev_chain_id
        # links it) - exclude those here so they're reached by walking
        # next_chain_id from their head instead of also listing as roots
        return [
            item_id for item_id in db.get_item_ids()
            if db.get_item_attr(item_id, "parent_id") is None
            and db.get_item_attr(item_id, "prev_chain_id") is None
        ]

    def _debug(args, kwargs):
        print("args:", args)
        print("kwargs:", kwargs)

    # CRUD
    def show_all(show_done=True):
        view_lists(db, Controller._get_root_ids(), show_done=show_done)

    def show_item(item_id: int|str, **kwargs):
        # not fatal on a miss (unlike _resolve_item) - a typo'd show target
        # shouldn't kill the session
        item = Controller._find_item_by_identifier(item_id)
        if item is None:
            print(f"Could not find item matching pattern '{item_id}'")
            return
        view_item(db, item.id, **kwargs)

    def show_filtered(tokens: list[str], **kwargs):
        """`task show attr<op>value ...` - render only the items matching all
        the given filters, each with its parent chain for context."""
        try:
            exprs = parse_filters(tokens)
        except FilterError as e:
            Controller.throw_error(str(e))
            return

        matched = match_items(db, exprs)
        if not matched:
            print("No items match those filters")
            return

        display = with_ancestors(db, matched)
        roots = [r for r in Controller._get_root_ids() if r in display]
        view_lists(
            db, roots,
            show_done=kwargs.get("show_done", True),
            only_ids=display,
        )
        print(f"\n{len(matched)} item{'s' if len(matched) != 1 else ''} matched")

    def show_examples():
        print(help_menu["examples"])

    def create_item(name: str, parent_id=None, **kwargs) -> int:
        if parent_id is not None:
            parent_id = Controller._resolve_item(parent_id).id

        kwargs = Controller._parse_item_kwargs(kwargs)
        item_id = db.create_item(name=name, parent_id=parent_id, **kwargs)
        print(f"Created item {item_id} - '{name}'")
        db.commit()
        return item_id

    def create_comment(item_id: int|str, content: str):
        item = Controller._resolve_item(item_id)
        comment_id = db.create_comment(content=content, item_id=item.id)
        print(f"Added comment {comment_id} to item {item.id} - '{content}'")
        db.commit()

    def update_item(item_id: int|str, recursive=False, **kwargs):
        item_id = Controller._resolve_item(item_id).id
        kwargs = Controller._parse_item_kwargs(kwargs)
        db.update_item(item_id, **kwargs)
        print(f"Updated item {item_id}")

        if recursive:
            children = db.get_item_attr(item_id, "child_ids")
            for child_id in children:
                Controller.update_item(child_id, recursive=True, **kwargs)

        db.commit()

    def delete_item(id_: int|str, chain: bool = False):
        item = Controller._resolve_item(id_)

        if chain:
            # walk back to the true head first, so this works no matter
            # which link in the chain was targeted
            head_id = item.id
            while True:
                prev_id = db.get_item_attr(head_id, "prev_chain_id")
                if prev_id is None:
                    break
                head_id = prev_id
            db.delete_chain(head_id)
            db.commit()
            print(f"Deleted chain starting at {head_id}")
            return

        db.delete_item(item.id)
        db.commit()
        print(f"Deleted item {item.id}")

    def delete_completed(parent_identifier=None):


        if parent_identifier is None:
            ids_to_check = db.get_item_ids()
        else:
            parent = Controller._resolve_item(parent_identifier)
            ids_to_check = Controller._flatten_item_descendants(parent)

        for item_id in ids_to_check:
            try:
                item: TodoItem = db.get_item(item_id)
            except:
                continue
            if item.completed:
                db.delete_item(item_id)
        db.commit()
    
    def ai_headstart(item_id: int|str):
        item = Controller._resolve_item(item_id)
        ai_response_text = ai_headstart_service(db, item.id)
        comment_content = f"AI: {ai_response_text}"
        Controller.create_comment(item.id, comment_content)
        print(comment_content)

    def ai_natural_language(prompt: str, **kwargs):
        ai_natural_language_service(
            db, prompt,
            context=kwargs.get("context"),
            reasoning=kwargs.get("reasoning"),
        )
    
    def throw_error(error_description: str, *args, verbose: bool = False, **kwargs):
        message = f"[red]ERROR: {error_description}[/red]"
        if verbose:
            message += f"\nargs={args}\nkwargs={kwargs}"
        print(message)
        raise TaskCLIError(error_description)
    
    def get_config_value(key: str):
        if key not in CLIConfig.model_fields:
            Controller.throw_error(f"Unknown config key '{key}'")
            return
        print(getattr(db.get_config(), key))

    def list_config():
        for k, v in db.get_config().model_dump().items():
            print(f"{k}={v}")

    def set_config_value(key: str, value: any):
        if key not in CLIConfig.model_fields:
            Controller.throw_error(f"Unknown config key '{key}'")
            return
        db.update_config(**{key: value})
        db.commit()
        print(f"setting {key}={value}")

    def remove_config_value(key: str):
        if key not in CLIConfig.model_fields:
            Controller.throw_error(f"Unknown config key '{key}'")
            return
        db.remove_config_value(key)
        db.commit()
        print(f"Reset {key} to its default")
    
    def run_setup_service():
        user_setup_service(db)

    def repair_service():
        repair_database_service(db)

    def move_item(item_id: int|str, parent_identifier: int|str):
        item = Controller._resolve_item(item_id)

        # remove from old parent
        if item.parent_id is not None:
            db.remove_child_from_parent(item.id, item.parent_id)

        # add to new parent
        if not parent_identifier:  # anything evaluating to false -> becomes a root item
            new_parent_id = None
        else:
            new_parent_id = Controller._resolve_item(parent_identifier).id

        db.update_item(item.id, parent_id=new_parent_id)
        if new_parent_id is not None:
            db.add_child_to_parent(item.id, new_parent_id)

        db.commit()

    def reorder(id1: int|str, id2: int|str, position: str):
        if position not in ("before", "after"):
            Controller.throw_error("position must be one of before, after")
            return

        child1 = Controller._resolve_item(id1)
        child2 = Controller._resolve_item(id2)
        parent = db.get_item(child1.parent_id)
        if parent is None:
            Controller.throw_error("Cannot reorder root items")
            return

        new_child_ids = []
        for child_id in parent.child_ids:
            if child_id == child1.id:
                continue
            if child_id == child2.id:
                new_child_ids.extend(
                    [child1.id, child2.id] if position == "before" else [child2.id, child1.id]
                )
                continue
            new_child_ids.append(child_id)
        db.update_item(parent.id, child_ids=new_child_ids)
        db.commit()

    def add_link(parent_id: int|str, child_id: int|str):
        parent: TodoItem = Controller._resolve_item(parent_id)
        child: TodoItem = Controller._resolve_item(child_id)

        if child.id not in parent.linked_ids:
            parent.linked_ids.append(child.id)
        db.update_item(parent.id, linked_ids=parent.linked_ids)
        db.commit()

    def remove_link(parent_id: int|str, child_id: int|str):
        parent: TodoItem = Controller._resolve_item(parent_id)
        child: TodoItem = Controller._resolve_item(child_id)

        if child.id not in parent.linked_ids:
            Controller.throw_error(
                f"'{child.name}' ({child.id}) is not linked under "
                f"'{parent.name}' ({parent.id})"
            )
        parent.linked_ids.remove(child.id)
        db.update_item(parent.id, linked_ids=parent.linked_ids)
        db.commit()

    def next_node(name: str, prev_identifier: int|str, **kwargs):
        node_id = Controller.create_item(name, **kwargs)
        prev_id = Controller._resolve_item(prev_identifier).id
        db.insert_node_into_chain(node_id, prev_id)
        db.commit()

    def insert_node_as_chain(node_identifier: int|str, prev_identifier: int|str):
        node = Controller._resolve_item(node_identifier)
        prev = Controller._resolve_item(prev_identifier)
        db.insert_node_into_chain(node.id, prev.id)
        db.commit()

    def remove_node_as_chain(node_identifier: int|str):
        node = Controller._resolve_item(node_identifier)

        # walk back to the chain's head before splicing node out, so we
        # know where to reattach it afterward
        head = node
        while head.prev_chain_id is not None:
            head = db.get_item(head.prev_chain_id)

        db.remove_node_from_chain(node.id)

        # pull it out of the sequence and into the head's parent's set of
        # children - a no-op if node itself was the head (already that
        # parent's child) or the head is itself a root (nothing to attach to)
        if node.id != head.id and head.parent_id is not None:
            db.update_item(node.id, parent_id=head.parent_id)
            db.add_child_to_parent(node.id, head.parent_id)

        db.commit()

    def nuke_database():
        if not Confirm.ask("[red]This will permanently delete ALL data. Are you sure?[/red]", default=False):
            print("Cancelled.")
            return
        db.remove()
        print("Database wiped - starting fresh.")

    def browser_service(port: int = 8000):
        subprocess.run([sys.executable, '-m', 'uvicorn', 'taskai.browser:app', '--reload', '--port', str(port)])
        


# utilities
def _parse_arg_string(arg_string: str) -> list[str]:
    """parses a string properly before dispatching it to the argument parser"""
    
    # scan for quote characters
    
    currently_enclosed = False
    current_quote_char = None
    quote_chars = ('"',"'")
    buffer = ""
    arg_parts = []
    for c in arg_string:
        if c == " ":
            if currently_enclosed:
                buffer += c
            else:
                arg_parts.append(buffer)
                buffer = ""
        elif c == current_quote_char:
            currently_enclosed = False
            current_quote_char = None
        
        elif c in quote_chars and not currently_enclosed:
            currently_enclosed = True
            current_quote_char = c
        else:
            buffer +=  c
    if buffer:
        arg_parts.append(buffer)
    return arg_parts

def _parse_remaining(remaining_args: list[str]) -> tuple[list, dict]:

    # parse flags

    #for i, _arg in enumerate(remaining_args):
    #    remaining_args[i] = _arg.replace(" ", "+-*/")
    #remaining_args = " ".join(remaining_args).replace("="," ").split(" ")
    #for i, _arg in enumerate(remaining_args):
    #    remaining_args[i] = _arg.replace("+-*/", " ")
    
    # outputs
    args = []
    kwargs = {}

    while remaining_args:
        next_arg = remaining_args.pop(0)
        if next_arg.startswith("--"):
            if "=" in next_arg:
                key, value = next_arg.split("=")
                kwargs[key] = value
            else:
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
                show_args = list(args[1:])
                if looks_like_filters(show_args):
                    Controller.show_filtered(show_args, **kwargs)
                else:
                    target = args[1] if len(args) > 1 else "all"
                    match target:
                        case "all": Controller.show_all(*args[2:], **kwargs)
                        case _: Controller.show_item(target, **kwargs)

            case "create":
                Controller.create_item(args[1], **kwargs)
            
            case "update":
                Controller.update_item(args[1], **kwargs)
        
            case "reorder":
                Controller.reorder(args[1], args[3], args[2])

            case "delete" | "remove":
                chain = "-chain" in args
                Controller.delete_item(args[1], chain=chain)

            case "comment":
                Controller.create_comment(*args[1:], **kwargs)
            
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
                    case _: Controller.ai_natural_language(" ".join(args[1:]), **kwargs)

            case "nuke":
                Controller.nuke_database()
            
            case "add":
                parent_identifier = args[1]
                item_name = args[2]
                Controller.create_item(item_name, parent_identifier, **kwargs)
            
            case "link":
                parent_identifier = args[1]
                item_identifier = args[2]
                Controller.add_link(parent_identifier, item_identifier)

            case "unlink":
                parent_identifier = args[1]
                item_identifier = args[2]
                Controller.remove_link(parent_identifier, item_identifier)

            case "complete" | "done":
                recursive = "-r" in args or "-recursive" in args
                Controller.update_item(args[1], completed=True, recursive=recursive)

            case "undone":
                recursive = "-r" in args or "-recursive" in args
                Controller.update_item(args[1], completed=False, recursive=recursive)

            case "next":
                prev_identifier = args[1]
                item_name = args[2]
                Controller.next_node(item_name, prev_identifier, **kwargs)

            case "chain":
                prev_identifier = args[1]
                node_identifier = args[2]
                Controller.insert_node_as_chain(node_identifier, prev_identifier)

            case "unchain":
                Controller.remove_node_as_chain(args[1])

            case "examples":
                Controller.show_examples()

            case "repair":
                Controller.repair_service()

            case "browser":
                port = int(args[1]) if len(args) > 1 else 8000
                Controller.browser_service(port)

            case "clear":
                if len(args) > 1:
                    parent_identifier = args[1]
                else:
                    parent_identifier = None
                Controller.delete_completed(parent_identifier=parent_identifier)

            case "move":
                Controller.move_item(args[1], args[2])

            case "rename":
                Controller.update_item(args[1], name=args[2])

            case "pomo":
                pomodoro_service(int(args[1]), int(args[2]))

            # developer use
            case "db":
                import orjson as json
                print_json(json.dumps(db.get_item(int(args[1])).model_dump()).decode())

            case "status":
                if len(args) < 3:
                    item_id, status_val = args[1], ""
                else:
                    item_id, status_val = args[1:3]
                Controller.update_item(item_id, status=status_val)

            case "exit" | "exit()" | "quit":
                return 0

            case _: Controller.throw_error("unrecognized command", *args, **kwargs)

    except TaskCLIError:
        # already printed by throw_error - just propagate so callers
        # (interactive REPL, entry_point, the browser) know it failed
        raise
    except Exception as e:
        Controller.throw_error(f"encountered exception '{e}'", *args, **kwargs)

    return 1


def interactive_program():
    # console = Console()
    # builtins.print = console.print

    response = ""
    last_show_command = [("show", "all"), {}]
    args = None
    kwargs = None

    _clear_screen()
    while True:

        try:

            # render last show command
            if last_show_command is not None:
                try:
                    execute_commands(*last_show_command[0], **last_show_command[1])
                except Exception as e:
                    print(e)

            Console().rule()
            
            # prompt user input
            response = Prompt.ask("Type your commands:", default=response)
            
            # parse commands
            args_remaining = _parse_arg_string(response)
            args, kwargs = _parse_remaining(args_remaining)
            if not args:
                _clear_screen()
                continue
            if args[0] == "task":
                args = args[1:]
            if not args:
                _clear_screen()
                continue

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
        return

    if argv[0] in ("help","--help"):
        print(help_menu["general"])
        return

    args, kwargs = _parse_remaining(argv)

    try:
        execute_commands(*args, **kwargs)
    except TaskCLIError:
        sys.exit(1)


if __name__ == "__main__":
    entry_point()
