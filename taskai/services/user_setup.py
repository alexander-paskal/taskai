"""
This service will handle user setup and configuration

Basically, we're going to have a set of steps that we're going to iterate through
"""
from taskai.json_dir_database import JsonDirectoryDatabase

from rich.prompt import Prompt
from rich import print
import os


def user_setup_service(
    db: JsonDirectoryDatabase
):
    
    config = db.config
    # setup gemini model
    print("Beginning setup")
    if "GEMINI_API_KEY" not in config:
        api_key = _get_gemini_api_key()
        if api_key:
            config["GEMINI_API_KEY"] = api_key
    else:
        print("gemini key already specified")
    
    if "GEMINI_MODEL" not in config:
        model = _select_gemini_model()
        if model:
            config["GEMINI_MODEL"] = model
    else:
        print("gemini model already specified")
    print("Setup complete! Use 'task config set|get|list' to interact with your configuration options")
    db.commit()

def _get_gemini_api_key() -> str|None:
    response = Prompt.ask("Please enter your Gemini API key (use '$--' to access env vars)")
    
    if response.startswith("$"):
        response = os.getenv(response[1:])
    if not response:
        return
    print(f"Storing: [green]{response}[/green]")
    return response


def _select_gemini_model():
    response = Prompt.ask(
        "Please select which Gemini model you would like:",
        choices=[
            "gemini-3.5-flash"
        ]
    )
    return response


if __name__ == "__main__":
    import os
    db = JsonDirectoryDatabase(
        ".taskai/task_db", user=os.getenv("USER")
    )
    db.connect()
    user_setup_service(db)