"""
This file defines services for calling an LLM.

All services are idempotent
"""
# standard lib
import json

# local
from taskai.json_dir_database import JsonDirectoryDatabase
from taskai.models import TodoItem, TodoList, Comment
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


    item:TodoItem = db.read(item_id)

    
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
            comment: Comment = db.read(comment_id)
            prompt += f"\n\t- {comment.content}"

    # return "Survey says go fuck yourself"

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
    
    # build user info
    user_info = []
    for id_ in db.lists:
        list: TodoList = db.read(id_)
        user_info.append(f"{list.id} {list.name}")
        for item_id in list.item_ids:
    
            item: TodoItem = db.read(item_id)
            if not item.completed:
                user_info.append(f"\t {item.id} {item.name}")
    user_info = "\n".join(user_info)

    # build ai prompt
    ai_prompt = f"""
You are a todo-list agent. Your job is to convert a natural language description from a user into a set
of CLI operations using our app. Here are a comprehensive list of operations that can be performed

{help_general}

Here are all of the user's list and task names, each prepended with their id

{user_info}

Here is the user's prompt: 

{prompt}
"""
    
    ai_prompt += """
Your response should be a JSON output with a valid list of commands, as specified by the description above.
Each command should be structured in the following format:
    {
        "command": ... -> the subcommand you want to use (omit the first 'task' here)
        "args": [...] -> the positional arguments to use
        "kwargs": {"..." : "...", ...} -> the keyword arguments to use. All keyword argument names should be prepended with '--' 
    }

Here is an example of a response that you could return:

```
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
```

It is ABSOLUTELY IMPERATIVE that your response be valid json, as your output is going to be parsed directly. Return NOTHING but the json output.

"""

    
    from google import genai

    print(ai_prompt)
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model_name,
        contents=prompt
    )

    try:
        response_json = json.loads(response.text)
        print(response_json)
    except json.JSONDecodeError:
        print(response.text)
        print("\n\ndecode error")
        import sys
        sys.exit(-1)

        
