# DEVPLAN

Roadmap for the browser UI, the AI layer rewrite, and polish. Organized as
incremental phases — each step should leave the app in a runnable state.

## Project overview

Read this section first if you're picking this up cold — it's everything
about the existing codebase you need to not rediscover from scratch.

**What this is.** `taskai-cli` is a Python CLI task manager (published to
PyPI as `taskai-cli`, entry point `task` → `taskai.cli:entry_point`,
`requires-python >= 3.12`). Single user per machine. Optional AI features
call out to an LLM.

**Data model — there are no "lists," only items.** Everything lives in
[taskai/models.py](taskai/models.py) as Pydantic models. `TodoItem` is a
generic tree node: `parent_id` + `child_ids` form the hierarchy (a root item
has `parent_id = None`); any item can be a parent of any other item to any
depth, and the same node type is used whether it's acting as a "list" or a
"task." Other `TodoItem` fields: `dependency_ids` (blocks-on), `linked_ids`
(soft link, not reparenting), `comment_ids`, `due_by`, `priority`, `status`,
`completed`, `description`, and unused-so-far recurrence fields
(`recurs_every`/`recurs_until`/`recur_keep_incomplete`). `Comment` is a
simple `{content, item_id, created_on}`. `UserData` is the whole-DB
container: `todo_items: dict[str, dict]`, `comments: dict[str, dict]`,
`config: dict`, `id_counter`. `CLIConfig` currently holds
`GEMINI_MODEL`/`GEMINI_API_KEY` (Phase 2 below plans migrating this to a
single `AI_MODEL` field once `aisuite` lands) plus `DISPLAY_STRING`/
`DISPLAY_COLORS` for CLI rendering.

**Storage.** [taskai/json_dir_database.py](taskai/json_dir_database.py):
`JsonDirectoryDatabase` — one JSON file per user under `.taskai/task_db/
<user>.json`. `connect()` loads the whole file into memory as a `UserData`
Pydantic instance; `commit()` dumps the whole thing back out. No real
transactions — every `update_item` re-validates the *entire* item through
Pydantic. Parent/child/comment id-lists are maintained by hand on both sides
of every relationship (e.g. `create_item` also appends to the parent's
`child_ids`), so it's easy for future changes to desync them if you touch
one side and not the other. The real dev database at
`.taskai/task_db/alexc.json` has live in-progress task data used for manual
testing — don't `nuke` it.

**CLI dispatch.** [taskai/cli.py](taskai/cli.py): a `Controller` class
(methods intentionally take no `self` — called as `Controller.foo(...)`, not
instantiated) holds all the CRUD/business logic. `execute_commands(*args,
**kwargs)` is one big `match` statement mapping subcommands (`show`,
`create`, `add`, `update`, `move`, `rename`, `delete`, `complete`/`done`,
`comment`, `depend`, `link`, `reorder`, `clear`, `status`, `config`, `ai`,
`pomo`, `repair`, `nuke`, `browser`, ...) to `Controller` calls. There's a
hand-rolled arg/kwarg parser (`_parse_arg_string`, `_parse_remaining`)
instead of `argparse`. `interactive_program()` is the REPL entered when
`task` runs with no arguments. The module connects to the database and loads
config **at import time** (`db = JsonDirectoryDatabase(...); db.connect()`
at module scope) — anything that imports `taskai.cli` triggers this, which
is why `taskai/browser.py` reuses `from taskai.cli import db` rather than
opening a second connection.

**Views.** [taskai/views.py](taskai/views.py): Rich-based tree rendering
(`view_lists`, `view_item`, `view_items`), display format configurable via
`DISPLAY_STRING`/`DISPLAY_COLORS`.

**AI services.** [taskai/services/ai.py](taskai/services/ai.py):
`ai_headstart_service` (single item → LLM suggests a next concrete step,
saved as a comment) and `ai_natural_language_service` (prompt → LLM returns
a JSON list of `{command, args, kwargs}` → executed through
`taskai.cli.execute_commands`, one call per entry). Both currently call
Gemini directly via `google-genai`; Phase 2 below covers migrating to
`aisuite`. The natural-language prompt embeds
[taskai/help_menu.py](taskai/help_menu.py)'s `help_general` string as the
LLM's command reference — **that file is the single source of truth for the
command surface, shown to humans via `task help` and to the LLM verbatim.
Keep it in sync with `execute_commands` whenever the command set changes**,
it's gone stale before.

**Known code quirks (found but intentionally not fixed — out of scope
unless you're told to fix them):**
- `Controller.update_item` (`cli.py`) resolves a non-numeric `item_id` via
  `_find_model_by_stringmatch` but assigns the *whole model object* back
  into `item_id` instead of pulling `.id` off it, so it's passed down to
  `db.update_item` as a model, not an id, and fails. This means `update`,
  `rename`, and `status` (all three route through `update_item`) only work
  reliably with a numeric id, not a name.
- `task show <id1>,<id2>,...` is documented in the README but
  `execute_commands`'s `show` case never dispatches to
  `Controller.show_items`/`view_items` — there's no wired path to it.

**Command reference:** don't re-derive this — read
[taskai/help_menu.py](taskai/help_menu.py)'s `help_general`, it's kept
accurate on purpose.

**Dev environment.** Two venvs exist; `.taskai-venv` is the one with
`pytest` and all runtime deps installed — `source .taskai-venv/bin/activate`
before running anything. Tests: `python -m pytest -q` from repo root (7
tests across `test/test_cli.py`, `test_execution.py`,
`test_json_dir_database.py`, `test_view.py`).

**Browser work — status as of this writing.** Work happens on the git
branch `browser`. The toolchain actually in use differs from this file's
"Ground rules" section below in two ways, both because working code already
existed when the decision came up and reuse won: **FastAPI + uvicorn**
(not stdlib `http.server`), and **`<canvas>` 2D rendering** (not SVG). See
Phase 1 below for what's built vs. still open.

**Keeping this doc and DEVLOG.md current:** see the ground rules.

## Ground rules

- **Always running.** No stub functions, no half-wired features. Every step
  below should be small enough to implement, run `task ...` (or load the
  page), and see it work before moving to the next step.
- **Less code wins.** Reuse existing plumbing (`Controller`, `execute_commands`,
  `JsonDirectoryDatabase`) instead of building parallel code paths. If a
  browser feature can be expressed as an existing CLI command string, send it
  through the same command pipeline rather than writing a bespoke handler.
- **No frontend framework.** Plain HTML/CSS/JS, `fetch`, and SVG for the DAG.
  No React/Vue/D3/build step/npm. A few small `.js` files loaded directly by
  the browser is fine.
- **Less Manual Testing.** When you're making edits, to save tokens, don't 
  exhaustively test every single change, especially if its a small one. We
  will do larger scale testing at the end of each phase. If there's testing
  that needs to be done before progressing, tell me what to run and i'll test
  myself.
- **Tight Scope.** I don't need you to flag everything that's broken or suboptimal.
  Doing so will make simple things take unnecessarily long. Stay very focused
  on the explicit task that I said to do.
- **Keep DEVLOG.md current.** After a meaningful chunk of work (not every
  tiny edit), add a dated entry to `DEVLOG.md` describing what changed and
  the current state of things. This file (`DEVPLAN.md`) is the plan;
  `DEVLOG.md` is the running record of what's actually been done, so a fresh
  session can pick up context without re-deriving it from `git log`.

---

## Phase 0 — Fixes required before building on top of things

These are bugs found while reading the existing code that the new work would
otherwise inherit or expose:

- [x] `services/ai.py`: `ai_natural_language_service` builds `ai_prompt`
      (task list + command grammar + instructions) but calls
      `generate_content(contents=prompt)` — the raw, uninstructed prompt.
      Fix to send `ai_prompt`.
- [x] `services/ai.py`: `_add_info` reads `db.get_item(id_)` instead of
      `db.get_item(item_id)`, and calls `_visited_set.add(...)` on a `dict`
      (`_visited_set = {}`) — both will throw on first recursive call. Fix
      before the natural-language service is usable at all.
- [x] `services/ai.py`: `ai_natural_language_service` parses the LLM's JSON
      command list but never executes it — it just prints. Wire it to call
      through the same command dispatcher used by `execute_commands` in
      `cli.py`, once per parsed `{command, args, kwargs}` entry.
- [x] `cli.py`: `execute_commands`'s except block does `raise e` before
      `Controller.throw_error(...)`, so the friendly error path is dead code.
      Remove the `raise e` (or gate it behind a `--debug` flag) so errors
      surface the same way in both the CLI and the web console.
- [x] `views.py`: `view_item`/`view_items` call `db.read(...)` and
      `db.items`, neither of which exist on `JsonDirectoryDatabase`
      (`get_item`/`get_item_ids` are the real methods). This is currently
      dead/broken code — fix it so `task show items ...` works, since the
      web console will exercise this path.

---

## Phase 1 — Browser view

The browser needs *some* backend to talk to. Rather than a second data layer,
add a small local HTTP server that serves the static frontend and exposes the
existing `Controller`/command pipeline as JSON endpoints. Use Python's
stdlib `http.server` — no new dependency, consistent with "less code."

### 1.1 — Minimal server + static page (skeleton, but running end to end)

- [ ] New module `taskai/web/server.py`: a `BaseHTTPRequestHandler` (or
      `http.server.ThreadingHTTPServer`) that serves static files from
      `taskai/web/static/` and one endpoint, `GET /api/tree`, returning the
      full task tree as JSON (walk `db.get_item_ids()` / `db.get_item()`,
      `model_dump()` each item).
- [ ] New CLI command `task web [port]` in `cli.py`'s dispatcher that starts
      the server and opens the default browser to `http://localhost:<port>`.
- [ ] `taskai/web/static/index.html` + `app.js`: fetch `/api/tree` on load
      and `console.log` it. That's the whole deliverable for this step —
      confirms the server, routing, and data path all work before any
      rendering exists.

### 1.2 — Command execution endpoint (shared mutation path)

- [ ] `POST /api/command` accepting `{ "input": "<raw command string>" }`.
      Reuse `_parse_arg_string` + `_parse_remaining` + `execute_commands`
      from `cli.py` directly (import, don't reimplement). Capture `print`
      output for the response (redirect `sys.stdout` for the duration of the
      call, or thread a `Console(record=True)` through) and return
      `{ "output": "...", "tree": {...} }`.
- [ ] This single endpoint becomes the only mutation path for the browser:
      the edit menu and the console both end up POSTing command strings
      here. No separate REST CRUD surface to build or keep in sync.

### 1.3 — DAG view (v1: static render)

- [ ] `dag.js`: hand-rolled layered layout — depth = distance from a root
      via `parent_id`, siblings spread horizontally under `child_ids`. No
      layout library; this tree structure makes a simple recursive x/y
      assignment sufficient.
- [ ] Render nodes as SVG `<rect>`/`<text>` groups, parent→child edges as
      `<line>`/`<path>`. Re-fetch `/api/tree` and re-render on load.

### 1.4 — DAG view (v2: full graph + interaction)

- [ ] Draw `dependency_ids` and `linked_ids` as a second edge style (dashed
      / different color) layered on top of the tree edges — this is what
      makes it a DAG rather than just a tree view.
- [ ] Pan (drag) and zoom (wheel) via SVG `viewBox` manipulation — no
      library needed for this at this scale.
- [ ] Click to select/highlight a node and its edges.
- [ ] Color/style nodes by `status` / `completed` (strike-through or dim for
      completed, matching the existing `views.py` CLI convention).

### 1.5 — Edit menu

- [ ] Collapsible side panel (CSS class toggle, no JS animation library).
      Double-click a DAG node opens it, populated from that node's tree data
      already in memory (no extra fetch needed).
- [ ] Form fields mirror the CLI's `--field value` set from the README table
      (`description`, `due_by`, `priority`, `status`, `completed`,
      `depends_on`).
- [ ] Save builds an `update <id> --field value ...` command string per
      changed field and posts it to `/api/command` (reusing 1.2) — the edit
      menu never talks to the database directly.
- [ ] After save, re-fetch `/api/tree` and re-render the DAG in place.

### 1.6 — Console

- [ ] Collapsible panel (bottom or side) with a scrollback `<div>` and a
      single-line input, styled like a terminal.
- [ ] On submit: POST the raw text to `/api/command`, append `input` +
      `output` to scrollback, then refresh the DAG the same way the edit
      menu does. This is the same interactive loop `interactive_program()`
      already implements — the browser console is just a UI over the same
      endpoint, not a new command grammar.
- [ ] Up-arrow history is a nice cheap addition (array + index, no library).

At the end of Phase 1 the DAG, edit menu, and console all funnel through one
`/api/command` endpoint and one `/api/tree` read — that's the "less code"
payoff of routing everything through the existing `Controller`.

---

## Phase 2 — AI tools

### 2.1 — Finish the natural-language service

- [ ] Depends on Phase 0 fixes (prompt bug, `_add_info` bug, actually
      executing parsed commands).
- [ ] Add the ability to inject extra context / tools / other agentic framework arguments
      supported by aisuite. 
- [ ] Have execution reuse the *same* command-string path as the web console
      (`execute_commands`, or the `/api/command` handler once it exists) so
      AI-issued commands and human-issued commands share one code path.
- [ ] Print the parsed command list before executing it (already partially
      there via `print(response_json)`) — cheap safety net given the parsed
      commands can include `delete`/`nuke`. Not a full confirmation prompt,
      just visibility.

### 2.2 — Switch to `aisuite`

- [ ] Add `aisuite` to `pyproject.toml` dependencies; drop the direct
      `google-genai` import from `services/ai.py`.
- [ ] Replace both call sites (`ai_headstart_service`,
      `ai_natural_language_service`) with `aisuite.Client()` and
      `client.chat.completions.create(model=model_name, messages=[...])`.
      Model strings become `provider:model`, e.g. `google:gemini-2.0-flash`
      or `openai:gpt-4o-mini` — this is what buys multi-provider support for
      free.
- [ ] `aisuite` reads provider credentials from standard provider env vars
      (`OPENAI_API_KEY`, `GOOGLE_API_KEY`, etc.), not from a key you pass in.
      Drop the `@config("GEMINI_API_KEY", "api_key")` plumbing entirely —
      one less thing to configure and one less place a secret sits in the
      plaintext user JSON db.
- [ ] Rename `CLIConfig.GEMINI_MODEL`/`GEMINI_API_KEY` to a single
      `AI_MODEL` field holding the `provider:model` string.

### 2.3 — Update setup script for `aisuite`

- [ ] `services/user_setup.py`: replace `_get_gemini_api_key` /
      `_select_gemini_model` with a single prompt for `AI_MODEL`
      (`provider:model`), plus a printed reminder to set the matching
      provider env var (e.g. "set `OPENAI_API_KEY` in your environment")
      rather than storing a key in the db.
- [ ] Update `help_menu.py` / README wherever `GEMINI_API_KEY`/
      `GEMINI_MODEL` are referenced (`task config set GEMINI_API_KEY ...`
      example in the README) to match the new config shape.

---

## Phase 3 — Polish

- [ ] **Frontend cleanup.** Once 1.3–1.6 are functional, split `app.js` into
      small single-purpose files (`api.js`, `dag.js`, `console.js`,
      `editmenu.js`) and delete anything exploratory left over from getting
      the DAG layout working. Still no bundler — just multiple `<script>`
      tags loaded in order.
- [ ] **Minimalist docs.** A short "Web UI" section in the README (how to
      run `task web`, one screenshot) covers most of it; only split into a
      separate `docs/` page if the README starts feeling long. Keep the
      "less code" principle applied to prose too — this doesn't need to be
      exhaustive.
- [ ] **UX pass.** Empty/loading state for the DAG when a user has no tasks
      yet (currently the app would just render nothing); a keyboard shortcut
      to toggle the console (e.g. backtick); consistent spacing/typography
      in `style.css`; visual legend distinguishing tree edges from
      dependency/link edges.
- [ ] Re-check the Phase 0 fixes are still holding once the web UI is
      exercising more command paths than the CLI alone did.
