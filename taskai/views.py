# local
from taskai.json_dir_database import JsonDirectoryDatabase, DatabaseError
from taskai.models import TodoItem, Comment
from taskai.config import config

# external
from rich import print
from rich.console import Console
import rich


"""
Lets give the lists a display string


set of valid attributes
- id
- name
- status
- 


"""


VALID_ATTRS = {
    "id",
    "name",
    "created_on",
    "due_by",
    "priority",
    "status"
}


@config("DISPLAY_STRING", "display_str")
@config("DISPLAY_COLORS", "display_colors")
def view_lists(
        db: JsonDirectoryDatabase, 
        roots: list[int], 
        show_done=True,
        max_level=1000,
        display_str: str = "id name status", 
        display_colors: str = None
):
    """Shows all the lists"""

    attrs = display_str.lower().split(" ")

    if display_colors:
        colors = display_colors.lower().split(" ")
        assert len(colors) == len(attrs), "must have a color for every attr"

    for attr in attrs:
        assert attr in VALID_ATTRS, "invalid attribute in display string {}".format(attr)

    def _render_display_string(item: TodoItem):
        display_string = ""
        for i, attr in enumerate(attrs):
            part = getattr(item, attr)
            if not part:
                continue
            part = str(part)
            if display_colors and colors[i] != "_":
                part = _wrap_string(part, f"[{colors[i]}]", f"[/{colors[i]}]")  
            display_string += f" {part}"
        display_string = _wrap_string(display_string, "[strike]", "[/strike]", condition=item.completed)
        return display_string

    def _print_item(item: TodoItem, level: int, prefix=""):
        if not show_done and item.completed:
            return
        
        display_string = _render_display_string(item)
        indent = "\t" * level
        print(indent + prefix + display_string)

    def _recursive_print(item_id: int, level: int):
        if level >= max_level:
            return

        try:
            item = db.get_item(item_id)
        except DatabaseError:
            return
        
        _print_item(item, level)


        for linked_id in item.linked_ids:
            try:
                linked_item = db.get_item(linked_id)
            except DatabaseError:
                continue
            _print_item(linked_item, level+1, prefix="-->")

        for child_id in item.child_ids:
            _recursive_print(child_id, level+1)


    for root in roots:
        _recursive_print(root, 0)
            

def view_item(
        db: JsonDirectoryDatabase, 
        item_id: int,
        show_done: bool = True
    ):
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
        view_lists(db, item.child_ids, show_done=show_done)

    if item.linked_ids:
        console.print("\n[bold green]\nLinked Items:[/bold green]")
        view_lists(db, item.linked_ids, show_done=show_done, max_level=1)

    
        # view_lists(db, item.linked_ids, show_done=show_done, max_level=1, prefix="-->")

def view_items(
    db: JsonDirectoryDatabase, 
    ids: list[str],
    sort_by: str  = "due_by",
    ascending: bool = False,
    show_done: bool = True
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
        view_item(db, item, show_done=show_done)
        print()



### Utils


def _wrap_string(string_, before, after=None, condition=True):
    if after is None:
        after = before
    
    if condition:
        return f"{before}{string_}{after}"
    else:
        return string_
