"""
This service will handle user setup and configuration

Basically, we're going to have a set of steps that we're going to iterate through
"""
from taskai.json_dir_database import JsonDirectoryDatabase
from taskai.llm_models import PROVIDER_ENV_VARS, PROVIDER_MODELS

from rich.prompt import Prompt
from rich import print


def user_setup_service(
    db: JsonDirectoryDatabase
):

    config = db.get_config()
    # setup ai model
    print("Beginning setup")
    if "AI_MODEL" not in config:
        model = _get_ai_model()
        if model:
            db.update_config(AI_MODEL=model)
    else:
        print("AI model already specified")
    print("Setup complete! Use 'task config set|get|list' to interact with your configuration options")
    db.commit()

def _select_from_list(prompt_text: str, options: list[str]) -> str:
    """Show a numbered menu of options; accept either a number or free text."""
    if options:
        print("\n".join(f"  {i}. {opt}" for i, opt in enumerate(options, 1)))
    response = Prompt.ask(prompt_text)
    if response.isdigit() and 1 <= int(response) <= len(options):
        return options[int(response) - 1]
    return response

def _get_ai_model() -> str|None:
    provider = _select_from_list(
        "\nSelect a provider (number or name)", list(PROVIDER_ENV_VARS)
    )
    if not provider:
        return

    model_options = PROVIDER_MODELS.get(provider, [])
    model = _select_from_list(
        f"\nSelect a model for '{provider}' (number or name)", model_options
    )
    if not model:
        return

    response = f"{provider}/{model}"
    print(f"Storing: [green]{response}[/green]")

    env_vars = PROVIDER_ENV_VARS.get(provider)
    if env_vars is None:
        print(
            f"Unrecognized provider '{provider}' - check litellm's docs for the "
            f"env var(s) it expects, and add it to PROVIDER_ENV_VARS in "
            f"llm_models.py if you use it regularly."
        )
    elif env_vars:
        print("Make sure these environment variables are set:\n" + "\n".join(f"  {v}" for v in env_vars))
    else:
        print(f"'{provider}' runs locally - no credentials needed.")
    return response


if __name__ == "__main__":
    import os
    db = JsonDirectoryDatabase(
        ".taskai/task_db", user=os.getenv("USER")
    )
    db.connect()
    user_setup_service(db)
