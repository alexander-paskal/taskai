# standard lib
from datetime import datetime

# local
from taskai.json_dir_database import JsonDirectoryDatabase, DatabaseError
from taskai.models import TodoItem, Comment
from taskai.config import config

# external
from rich import print
from rich.color import Color, ColorParseError
from rich.console import Console


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
    "due",
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
        only_ids: set[int] | None = None,
        display_str: str = "id name status",
        display_colors: str = None
):
    """Shows all the lists.

    `only_ids`, when given, prunes the walk to just those ids - used by
    `task show <filters>` to render matched items with their parent chain
    and nothing else.
    """

    attrs = display_str.lower().split(" ")

    if display_colors:
        colors = display_colors.lower().split(" ")
        assert len(colors) == len(attrs), "must have a color for every attr"

    for attr in attrs:
        assert attr in VALID_ATTRS, "invalid attribute in display string {}".format(attr)

    def _render_display_string(item: TodoItem):
        display_string = ""
        item_color = _rich_color(item.color)
        for i, attr in enumerate(attrs):
            part = getattr(item, attr)
            if not part:
                continue
            part = _format_date(part) if isinstance(part, datetime) else str(part)
            # an item's own color beats the column colors: it's drawn entirely in it
            color = item_color or (colors[i] if display_colors and colors[i] != "_" else None)
            if color:
                part = _wrap_string(part, f"[{color}]", f"[/{color}]")  
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

        if item_id in already_seen:
            return
        already_seen.add(item_id)


        if level >= max_level:
            return
        if only_ids is not None and item_id not in only_ids:
            return

        try:
            item = db.get_item(item_id)
        except DatabaseError:
            return

        _print_item(item, level)


        for linked_id in item.linked_ids:
            if only_ids is not None and linked_id not in only_ids:
                continue
            try:
                linked_item = db.get_item(linked_id)
            except DatabaseError:
                continue
            _print_item(linked_item, level+1, prefix="-->")

        for child_id in item.child_ids:
            _recursive_print(child_id, level+1)

        if item.next_chain_id is not None:
            print("\t" * level + "    \u2193")
            _recursive_print(item.next_chain_id, level)

    already_seen = set()
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
    item_color = _rich_color(item.color)
    name = _wrap_string(item.name, f"[{item_color}]", f"[/{item_color}]", condition=bool(item_color))
    console.print(f"[bold green]Name:[/bold green] {name}")
    if item.due:
        console.print(f"[bold green]Due:[/bold green] {_format_date(item.due)}")
    
    if item.description:
        console.print(f"\n[bold green]Description:[/bold green]\n{item.description}")
    
    if item.comment_ids:
        console.print("\n[bold green]\nComments:[/bold green]")
        for comment_id in item.comment_ids:
            comment: Comment = db.get_comment(comment_id)
            console.print(f"{_format_date(comment.created_on)} - {comment.content}")
    
    if item.child_ids:
        console.print("\n[bold green]\nSubtasks:[/bold green]")
        view_lists(db, item.child_ids, show_done=show_done)

    if item.linked_ids:
        console.print("\n[bold green]\nLinked Items:[/bold green]")
        view_lists(db, item.linked_ids, show_done=show_done, max_level=1)

    
        # view_lists(db, item.linked_ids, show_done=show_done, max_level=1, prefix="-->")


### Utils

# CSS color names Rich has no name for (its named colors come from the 256-color
# ANSI palette), so an item colored "orange" in the browser can still be shown
_CSS_COLORS_MISSING_IN_RICH = {
    "orange": "#ffa500", "pink": "#ffc0cb", "gold": "#ffd700", "teal": "#008080",
    "brown": "#a52a2a", "indigo": "#4b0082", "violet": "#ee82ee", "crimson": "#dc143c",
    "coral": "#ff7f50", "salmon": "#fa8072", "lime": "#00ff00", "olive": "#808000",
    "navy": "#000080", "maroon": "#800000", "silver": "#c0c0c0", "gray": "#808080",
    "grey": "#808080",
}


def _rich_color(css_color: str | None) -> str | None:
    """An item's `color` (a CSS color string, e.g. "#ff8844" or "green") as a
    Rich color, or None when it's unset or isn't one Rich can draw - an
    unusable color just isn't shown rather than breaking the whole listing."""
    if not css_color:
        return None
    css_color = css_color.strip().lower()
    for candidate in (css_color, _CSS_COLORS_MISSING_IN_RICH.get(css_color)):
        if not candidate:
            continue
        try:
            Color.parse(candidate)
        except ColorParseError:
            continue
        return candidate
    return None


def _format_date(value: datetime) -> str:
    """How every date is shown in the CLI: just the day, MM/DD/YY - the time
    of day is never displayed."""
    return value.strftime("%m/%d/%y")


def _wrap_string(string_, before, after=None, condition=True):
    if after is None:
        after = before
    
    if condition:
        return f"{before}{string_}{after}"
    else:
        return string_
