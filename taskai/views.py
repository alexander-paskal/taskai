# local
from taskai.json_dir_database import JsonDirectoryDatabase
from taskai.models import TodoItem, Comment

# external
from rich import print
from rich.console import Console
import rich


def view_lists(
        db: JsonDirectoryDatabase, 
        roots: list[int], 
        show_done=True, 
):
    """Shows all the lists"""


    def _print_item(item: TodoItem, level: int):
        if not show_done and item.completed:
            return
        display_string = f"{item.id} {item.name}"
        display_string = _wrap_string(display_string, "[strike]", "[/strike]", condition=item.completed)
        indent = "\t" * level
        print(indent + display_string)

    def _recursive_print(item_id: int, level: int):
        item = db.get_item(item_id)
        _print_item(item, level)
        for child_id in item.child_ids:
            _recursive_print(child_id, level+1)

    for root in roots:
        _recursive_print(root, 0)
            

def view_item(db: JsonDirectoryDatabase, item_id: int):
    """Show details for item"""

    item = db.get_item(item_id)

    console = Console()
    console.print(f"[bold green]Name:[/bold green] {item.name}")
    if item.due_by:
        console.print(f"[bold green]Due By:[/bold green] {item.due_by or ""}")
    
    if item.description:
        console.print(f"\n[bold green]Description:[/bold green]\n{item.description}")
    
    if item.dependency_ids:
        console.print(f"\n[bold green]Depends on:[/bold green]{''.join([
            f'\n{depend_id} - {db.read(depend_id).name}' for depend_id in item.dependency_ids 
        ])}")

    if item.comment_ids:
        console.print("\n[bold green]\nComments:[/bold green]")
        for comment_id in item.comment_ids:
            comment: Comment = db.get_comment(comment_id)
            console.print(f"{comment.created_on.strftime("%Y-%m-%d %H:%M:%S")} - {comment.content}")
    
    if item.child_ids:
        console.print("\n[bold green]\nSubtasks:[/bold green]")
        view_lists(db, item.child_ids)

def view_items(
    db: JsonDirectoryDatabase, 
    ids: list[str],
    sort_by: str  = "due_by",
    ascending: bool = False
):
    
    items = {}
    for id_ in ids:
        if id_ in db.items:
            item = db.read(id_)
            items[id_] = (item)
    
    # sort
    items = sorted(items.values(), key=lambda item: str(getattr(item, sort_by)), reverse=ascending)

    # view
    for item in items:
        rich.console.Console().rule(style="bold white")
        view_item(db, item)
        print()



### Utils


def _wrap_string(string_, before, after=None, condition=True):
    if after is None:
        after = before
    
    if condition:
        return f"{before}{string_}{after}"
    else:
        return string_