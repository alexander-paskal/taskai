import contextlib
import io
import os

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from taskai.cli import Controller, _parse_arg_string, _parse_remaining, db, execute_commands


app = FastAPI()

# get baspath to static
static_abs_dir = os.path.join(os.path.dirname(__file__), "static")


app.mount("/static", StaticFiles(directory=static_abs_dir), name="static")

@app.get("/", response_class=FileResponse)
def index():
    return FileResponse(os.path.join(static_abs_dir, "index.html"))


def _full_tree():
    return {
        item_id: db.get_item(item_id).model_dump(mode="json")
        for item_id in db.get_item_ids()
    }


@app.get("/api/tree")
def get_tree():
    db.flush()  # reload from disk in case another process (e.g. the CLI) wrote since we last connected
    return _full_tree()


class CommandRequest(BaseModel):
    input: str


@app.post("/api/command")
def run_command(request: CommandRequest):
    arg_parts = _parse_arg_string(request.input)
    args, kwargs = _parse_remaining(arg_parts)

    if not args:
        return {"output": "", "tree": _full_tree(), "focus": None}

    if args[0] == "show":
        return _run_show(args)

    output = io.StringIO()
    try:
        with contextlib.redirect_stdout(output):
            execute_commands(*args, **kwargs)
    except SystemExit:
        pass  # Controller.throw_error() prints the error, then calls sys.exit(-1)

    return {"output": output.getvalue(), "tree": _full_tree(), "focus": None}


def _run_show(args):
    """`show` is read-only from the browser's perspective: it never mutates
    the db, it just tells the frontend which node to focus/center on."""
    target = args[1] if len(args) > 1 else "all"

    if target == "all":
        return {"output": "", "tree": _full_tree(), "focus": None}

    if target == "examples":
        return {"output": "Not implemented yet", "tree": _full_tree(), "focus": None}

    item = Controller._find_item_by_identifier(target)
    if item is None:
        return {
            "output": f"Could not find item matching pattern '{target}'",
            "tree": _full_tree(),
            "focus": None,
        }

    return {"output": "", "tree": _full_tree(), "focus": str(item.id)}
