"""
This file defines services for calling an LLM.

All services are idempotent
"""
# standard lib
import json

# local
from taskai.json_dir_database import JsonDirectoryDatabase
from taskai.models import TodoItem, Comment
from taskai.config import config
from taskai.help_menu import help_general

@config("GEMINI_API_KEY", "api_key")
@config("GEMINI_MODEL", "model_name")
def ai_headstart_service(
        db: JsonDirectoryDatabase,
        item_id: str,
        api_key: str,
        model_name: str
):
    """
    This service queries an LLM for your task and asks it to give you
    a headstart on a given task. It will perform the following operations:

    - Compile the context for the query, including task description, dependencies
    and previous comments
    - Query the LLM
    - Parse and return its response
    """

    item:TodoItem = db.get_item(item_id)

    
    from google import genai
    


    # contruct prompt
    prompt = f"""
Hi Gemini, you're job is to provide a very succinct headstart for a taskai item.
This will involve the following:
- parsing the task information, including description, comments and dependencies
- performing any necessary internet searches in order to acquire relevant information
- deciding on what the next immediate step to be taken is
- returning a very succinct command to the user, with the information necessary to execute that command


Examples of good responses:

"Call the florist: 443-869-2158"
"Email HR @ hr@comapany.com 'Hi, I won't be able to make it in today'"
"Write the natural language service interface:\ndef natural_language_service(db:):\n\t..."

These should be short and to the point. Your response should contain NOTHING but the comment for the user.

Here's the relevant information:

task name: {item.name}
"""

    if item.description:
        prompt += f"\ntask description: {item.description}"
    if item.comment_ids:

        prompt += f"\ntask comments:"
        for comment_id in item.comment_ids:
            comment: Comment = db.get_comment(comment_id)
            prompt += f"\n\t- {comment.content}"
    # query model
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model_name,
        contents=prompt
    )

    return response.text

@config("GEMINI_API_KEY", "api_key")
@config("GEMINI_MODEL", "model_name")
def ai_natural_language_service(
    db: JsonDirectoryDatabase,
    prompt: str,
    api_key: str,
    model_name: str
):
    """
    This service queries an LLM with a natural language
    prompt from the user. The response is a series of terminal commands
    called directly
    """
    print(f"Ai prompt: {prompt}")
    
    # recursively build user info
    user_info = []
    _visited_set = set()

    def _add_info(item_id, level=0):
        item: TodoItem = db.get_item(item_id)
        user_info.append("  "*level + f"{item.id} {item.name}")
        _visited_set.add(item_id)
        if item.child_ids:
            for child_id in item.child_ids:
                if child_id not in _visited_set:
                    _add_info(child_id, level+1)


    for id_ in db.get_item_ids(): 
        if id_ not in _visited_set:
            _add_info(id_)

    user_info = "\n".join(user_info)

    # build ai prompt
    ai_prompt = f"""
You are a todo agent. Your job is to convert a natural language description from a user into a set
of CLI operations using our app. Here are a comprehensive list of operations that can be performed

{help_general}

Here are all of the user's existing item names, each prepended with their id

{user_info}

Here is the user's prompt:

{prompt}
"""

    ai_prompt += """
Rules for referencing items (read this carefully, mistakes here will make commands fail):
- Commands run in the order you list them, top to bottom.
- There is no separate "list" concept - everything is an item, and items form a tree. 'create' adds
  a new top-level (root) item. 'add' adds a new item as a child of an EXISTING parent item - the
  parent must already exist, either in the item names above or created earlier in this same batch.
- Every id or name you reference as a TARGET (a parent, an item to update/move/link/depend-on/etc.)
  must be either: (a) an id or exact name from the existing item names above, or (b) an item you
  create earlier in this same list of commands, referenced afterward by the exact name you gave it
  in that earlier 'create'/'add' command.
- If the user mentions an item that does not already exist above, add a 'create' (top-level) or
  'add' (child of an existing parent) command for it BEFORE any command that references it. Never
  reference an item that neither exists above nor was created earlier in this batch.
- Prefer numeric ids over names whenever an id is available - they're unambiguous. The following
  commands only work correctly with an id, never a name: update, rename, status, comment, complete,
  done, depend, reorder.
- Only use the commands and '--field' names listed above. Do not invent new ones.

Your response should be a JSON output with a valid list of commands, as specified by the description above.
Each command should be structured in the following format:
    {
        "command": ... -> the subcommand you want to use (omit the first 'task' here)
        "args": [...] -> the positional arguments to use
        "kwargs": {"..." : "...", ...} -> the keyword arguments to use. All keyword argument names should be prepended with '--' 
    }

Here is an example of a response that you could return:

[
    {
        "command": "add",
        "args": ["Daily", "Take out the trash"],
        "kwargs": {"--description": "some description"}
    },
    {
        "command": "add",
        "args": ["Daily", "Walk the dog"]
    },
    {
        "command": "delete",
        "args": ["Old Daily List"]
    }
]


It is ABSOLUTELY IMPERATIVE that your response be valid json, as your output is going to be parsed directly. Return NOTHING but the json output. do NOT wrap it in ``` or any other
markdown formatting. Just the raw json string.

"""

    
    from google import genai

    print(ai_prompt)
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model_name,
        contents=ai_prompt
    )

    try:
        response_json = json.loads(response.text)
    except json.JSONDecodeError:
        print(response.text)
        print("\n\ndecode error")
        import sys
        sys.exit(-1)

    print(response_json)

    from taskai.cli import execute_commands

    for entry in response_json:
        command = entry["command"]
        cmd_args = entry.get("args", [])
        cmd_kwargs = {
            k.lstrip("-"): v
            for k, v in entry.get("kwargs", {}).items()
        }
        execute_commands(command, *cmd_args, **cmd_kwargs)

