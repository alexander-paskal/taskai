"""Sphinx configuration for the taskai documentation.

Built and hosted by Read the Docs (see ``/.readthedocs.yaml``). To build it
locally:

    pip install -r docs/requirements.txt
    sphinx-build -b html docs docs/_build/html

Open ``docs/_build/html/index.html`` in a browser, or use ``sphinx-autobuild``
for live reload.
"""
import sys
from importlib.metadata import PackageNotFoundError, version as _pkg_version
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent

# -- Project information ------------------------------------------------------

project = "taskai"
author = "Alex Paskal"
copyright = "2026, Alex Paskal"


def _project_version() -> str:
    """The version to display. Prefers installed package metadata, falls back
    to reading pyproject.toml (Read the Docs doesn't install the package), then
    to a placeholder."""
    try:
        return _pkg_version("taskai-cli")
    except PackageNotFoundError:
        pass
    try:
        import tomllib

        data = tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text("utf-8"))
        return data["project"]["version"]
    except Exception:
        return "0.0.0"


release = _project_version()
version = release

# -- General configuration ---------------------------------------------------

extensions = [
    "myst_parser",
    "sphinx_copybutton",
    "sphinx_design",
]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

myst_enable_extensions = [
    "colon_fence",  # ::: fenced directives
    "deflist",
]

exclude_patterns = ["_build", "_generated", "Thumbs.db", ".DS_Store"]

# -- HTML output -------------------------------------------------------------

html_theme = "furo"
html_title = f"taskai {release}"
# NOTE: confirm the Read the Docs project slug and adjust if it isn't "taskai"
# (this also appears in the README). Read the Docs sets the per-version
# canonical URL itself; this is just the site root.
html_baseurl = "https://taskai.readthedocs.io/"
html_static_path = ["_static"]

html_theme_options = {
    "source_repository": "https://github.com/alexander-paskal/taskai/",
    "source_branch": "main",
    "source_directory": "docs/",
}

# -- Generated content: single source of truth ------------------------------
#
# `taskai/help_menu.py` holds the canonical command surface as a plain string
# (`task help` prints `help_general` verbatim, and the AI layer is shown the
# same text). `taskai/llm_models.py` holds the provider -> env-var map. Rather
# than copy any of that into the docs and let it drift, we dump it to files
# under docs/_generated/ at build time and pull those in with `literalinclude`
# / `{include}`. The generated files are git-ignored (see docs/.gitignore).
#
# help_menu.py and llm_models.py have no third-party imports and do not touch
# the database, so importing them here is cheap and side-effect free.


def _write_generated(app=None) -> None:
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))

    from taskai.help_menu import help_general
    from taskai.llm_models import PROVIDER_ENV_VARS

    out = Path(__file__).parent / "_generated"
    out.mkdir(exist_ok=True)

    (out / "help_general.txt").write_text(help_general.strip() + "\n", "utf-8")

    rows = ["| Provider | Environment variable(s) |", "|---|---|"]
    for provider, envs in PROVIDER_ENV_VARS.items():
        cell = ", ".join(f"`{e}`" for e in envs) if envs else "_(none — runs locally)_"
        rows.append(f"| `{provider}` | {cell} |")
    (out / "providers.md").write_text("\n".join(rows) + "\n", "utf-8")


def setup(app):
    # builder-inited fires before any source is read, so the generated files
    # exist by the time literalinclude/include resolve them.
    app.connect("builder-inited", _write_generated)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
