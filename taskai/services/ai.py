"""
This file defines services for calling an LLM.

All services are idempotent
"""
from taskai.json_dir_database import JsonDirectoryDatabase
from taskai.models import TodoItem, TodoList, Comment
from taskai.config import config
import os
import json
from dotenv import load_dotenv
load_dotenv()


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

task title: {item.title}
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


def ai_natural_language_service(
    db: JsonDirectoryDatabase,
    prompt: str
):
    """
    This service queries an LLM with a natural language
    prompt from the user. The response is a series of terminal commands
    called directly
    """
    print(f"Ai prompt: {prompt}")

    command_help = ""
    
    # build user info
    user_info = []
    for id_ in db.lists:
        list: TodoList = db.read(id_)
        user_info.append(f"{list.id} {list.name}")
        for item_id in list.item_ids:
    
            item: TodoItem = db.read(item_id)
            if not item.completed:
                user_info.append(f"\t {item.id} {item.title}")
    user_info = "\n".join(user_info)

    # build ai prompt
    ai_prompt = f"""
You're job is to convert a natural language description for a user into a set
of operations on a database. Here are a comprehensive list of operations that can be performed

{command_help}

Here are all of the user's list and task titles, each prepended with their id

{user_info}
"""
    
    ai_prompt += """
Return your response in a json format, i.e.

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

"""

    ai_prompt += f"""
Here is the user's prompt: 

{prompt}
"""
    
    from google import genai

    print(ai_prompt)
    client = genai.Client(api_key=API_KEY)
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt
    )

    try:
        response_json = json.loads(response.text)
    except json.JSONDecodeError:
        print(response.text)
        print("\n\ndecode error")
        import sys
        sys.exit(-1)

        
