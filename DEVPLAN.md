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
- `Controller.update_item` never calls `Controller._parse_item_kwargs`
  (`create_item` does) before handing kwargs to `db.update_item`. Confirmed
  effects: `update <id> --due_by MM-DD-YYYY` throws a pydantic validation
  error (the string never gets converted to a `datetime`, unlike on
  `create`), and `update <id> --depends_on 1,2` silently no-ops (never
  remapped to the model's real `dependency_ids` field, so pydantic just
  drops it as an unrecognized extra key — no error, no effect). Every other
  field (`name`, `description`, `status`, `priority`, `completed`) updates
  correctly. The edit panel (1.5) and console both go through `update` and
  will hit this. Likely fix: add the same
  `kwargs = Controller._parse_item_kwargs(kwargs)` call `create_item` makes.

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

- [x] `POST /api/command` accepting `{ "input": "<raw command string>" }`,
      in `taskai/browser.py`. Reuses `_parse_arg_string` + `_parse_remaining`
      + `execute_commands` from `cli.py` (imported, not reimplemented).
      Response shape ended up `{ "output": "...", "tree": {...}, "focus":
      "<id>"|null }` — the extra `focus` field exists because `show` is
      special-cased: it never touches `execute_commands` (it's read-only
      from the browser's perspective), it just resolves a target id and
      returns it as `focus` so the frontend can call `focusOnNode` on it
      instead of getting text output back. Everything else runs through
      `execute_commands` normally with stdout captured via
      `contextlib.redirect_stdout`.
- [x] Found and worked around a real landmine while building this:
      `Controller.throw_error` calls `sys.exit(-1)`, which raises
      `SystemExit` — not an `Exception`, so `execute_commands`'s own
      `except Exception` never catches it. Any unrecognized command or bad
      args (very common from a console) would throw `SystemExit` straight
      through the request handler. Caught at the server boundary only
      (`cli.py` untouched, so CLI behavior is unchanged) so bad input
      degrades to an error string instead.
- [x] This single endpoint is now the only mutation path for the browser —
      both the edit menu (1.5) and the console (1.6) POST through it.

### 1.3 — DAG view (v1: static render)

- [x] `dag.js`: hand-rolled layered layout — depth = distance from a root
      via `parent_id`, siblings spread horizontally under `child_ids`. No
      layout library; this tree structure makes a simple recursive x/y
      assignment sufficient. Lives in `canvas.js` (see toolchain note above),
      not a separate `dag.js`.
- [x] Render nodes — done as `<canvas>` 2D shapes (rounded squares + text),
      not SVG `<rect>`/`<text>`, consistent with the canvas-not-SVG decision
      already noted above. Re-fetches `/api/tree` and re-renders on load.

### 1.4 — DAG view (v2: full graph + interaction)

- [ ] Draw `dependency_ids` and `linked_ids` as a second edge style (dashed
      / different color) layered on top of the tree edges — this is what
      makes it a DAG rather than just a tree view. Still open — only
      parent/child tree edges render today.
- [x] Pan (drag) and zoom (wheel) — done via canvas context transforms
      (`ctx.translate`/`ctx.scale` + a `view` state object), not SVG
      `viewBox`, same toolchain reasoning as above. Zoom keeps the point
      under the cursor fixed. Also added beyond the original plan:
      double-click a node to ease the view to center + zoom on it
      (`focusOnNode` in `canvas.js`).
- [x] Click to select a node — single click (double-click stays taken by
      center/zoom). `selectedNode` in `canvas.js` persists across hover and
      redraws, and is re-resolved by id after every tree refresh (a command
      response rebuilds all node objects from scratch, so the old reference
      would otherwise silently dangle and the selection would appear to
      break after any mutation). Drawn with the same accent-blue
      border/thicker stroke as hover. This is exactly the state 1.5's edit
      menu piggybacks off — not edge highlighting yet, just the node.
- [x] Color/style nodes by `completed` — soft green fill + border (see
      `STYLE.colors.nodeFill/BorderDone`), not strike-through/dim like the
      CLI. `status` ended up as a small orange text label in the node's
      top-right corner (`STYLE.colors.statusText`) rather than a node-wide
      recolor, since status is a free-form string, not a small fixed set of
      states — recoloring the whole node didn't make sense for arbitrary
      text.

Also done, ahead of plan: hover now highlights the node (border + fill tint)
and shows a tooltip with its full, untruncated label — labels are truncated
with an ellipsis to fit inside the node otherwise. Visual styling (colors,
node size/shape, spacing, zoom bounds, font) is centralized in a `STYLE`
config object at the top of `canvas.js`, kept as plain data on purpose so it
can later be served from a `GET /api/style` endpoint instead of hardcoded —
add new visual knobs there, not inline in `draw()`.

### 1.5 — Edit menu

- [x] Collapsible panel — ended up right-side (not left/bottom), in
      `taskai/static/editpanel.js` + `.edit-panel` in `style.css`. Collapsed
      state is just a bare `44px` chevron button (no visible bar/background)
      pinned to its own top-left corner; expanded is a `320px` white panel.
      Toggling animates the canvas's width/pan/zoom in step with the panel
      over the same 200ms as its CSS transition (`setRightPanelWidth` in
      `canvas.js`), rescaling zoom in proportion to the width change (not
      just re-panning) so the same amount of graph content stays visible
      instead of getting cropped. Populated by clicking a DAG node (1.4's
      selection), from `latestItemsById` (the full `/api/tree`-shaped data
      canvas.js already has) — no extra fetch.
- [x] Form fields: `name`, `description`, `status`, `priority`, `due_by`,
      `completed`, `dependency_ids` (labeled "Depends on"). Added `name`
      beyond the README's `--field` table since it's directly editable data,
      not just renameable via a separate command. Each field's input type
      matches its data: text/textarea/number/date/checkbox; `due_by` round-
      trips `<input type="date">`'s `YYYY-MM-DD` to/from the CLI's
      `MM-DD-YYYY`; `dependency_ids` round-trips to/from the CLI's
      comma-separated `depends_on` id list.
- [x] **No Save button** — deliberate deviation from the original plan.
      Every field change posts straight to `/api/command` as
      `update <id> --<field> <value>`. Checkbox sends immediately on toggle;
      everything else listens on `input` and debounces 1s per field (keyed
      by item+field, so editing `name` doesn't reset `description`'s timer)
      so typing doesn't spam a request per keystroke.
- [x] After each update, the response's `tree` is applied in place (same
      `applyTree` the console uses) — no separate re-fetch needed.

While wiring this up, confirmed against a throwaway test item (created and
deleted, not real data): `name`/`description`/`priority`/`completed` all
update correctly end to end. `due_by` and `depends_on` hit the
`update_item`/`_parse_item_kwargs` bug documented above — left unfixed on
purpose, current call.

### 1.6 — Console

- [x] Collapsible panel, bottom-anchored (`taskai/static/console.js` +
      `.console-panel` in `style.css`) — `44px` collapsed strip with a
      double-chevron toggle, `280px` expanded, scrollback `<div>` +
      single-line input styled like a terminal (monospace, dark-on-light to
      match the rest of the theme).
- [x] On submit: POSTs to `/api/command`, appends output to scrollback, and
      applies the returned tree (`applyTree`) in place — matches the plan,
      except there's no separate "refresh the DAG" step since the command
      response already carries the fresh tree. Also handles the `focus`
      field `show` commands return: calls `focusOnNode` on that id instead
      of expecting text output.
- [ ] Up-arrow history — still open, not done.

At the end of Phase 1: dependency/link edges (1.4) and up-arrow console
history (1.6) are the only pieces left open. The DAG, edit panel, and
console all funnel through one `/api/command` endpoint and one `/api/tree`
read, as planned — that's the "less code" payoff of routing everything
through the existing `Controller`.

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
