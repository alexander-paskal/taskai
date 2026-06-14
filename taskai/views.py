# local
from taskai.json_dir_database import JsonDirectoryDatabase
from taskai.models import TodoList, TodoItem, Comment

# external
from rich import print
from rich.console import Console
import rich


def view_lists(db: JsonDirectoryDatabase, ids: list[str], show_done=False, show_items=True):
    """Shows all the lists"""

    
    for id_ in ids:

        if id_ in db.lists:
            list: TodoList = db.read(id_)
        elif isinstance(id_, str):
            for lid in db.lists:
                list = db.read(lid)
                if list.name.lower() == id_.lower():
                    break
            else: 
                raise RuntimeError("cannot match list")

        print(list.id, list.name)
        if show_items:
            for item_id in list.item_ids:

                # silently repair lists with
                if (item_id not in db.items):
                    list.item_ids.remove(item_id)
                    continue
                    
                item: TodoItem = db.read(item_id)
                if not item.completed:
                    print("\t",item.id, item.title)
                elif show_done:
                    print(f"\t [strike]{item.id} {item.title}[/strike]")


def view_item(db: JsonDirectoryDatabase, item: str|TodoItem):
    """Show details for item"""
    
    if isinstance(item, (str,int)):
        item: TodoItem = db.read(item)
    console = Console()
    console.print(f"[bold green]Title:[/bold green] {item.title}")
    if item.due_by:
        console.print(f"[bold green]Due By:[/bold green] {item.due_by or ""}")
    
    if item.description:
        console.print(f"\n[bold green]Description:[/bold green]\n{item.description}")
    
    if item.dependency_ids:
        console.print(f"\n[bold green]Depends on:[/bold green]{''.join([
            f'\n{depend_id} - {db.read(depend_id).title}' for depend_id in item.dependency_ids 
        ])}")

    if item.comment_ids:
        console.print("\n[bold green]\nComments:[/bold green]")
        for comment_id in item.comment_ids:
            comment: Comment = db.read(comment_id)
            console.print(f"{comment.created_on.strftime("%Y-%m-%d %H:%M:%S")} - {comment.content}")
    

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
        elif id_ in db.lists:
            list: TodoList = db.read(id_)
            for item_id in list.item_ids:
                item = db.read(item_id)
                items[item_id] = item
    
    
    # sort
    items = sorted(items.values(), key=lambda item: str(getattr(item, sort_by)), reverse=ascending)

    # view
    for item in items:
        rich.console.Console().rule(style="bold white")
        view_item(db, item)
        print()
