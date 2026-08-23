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
`config: dict`, `id_counter`. `CLIConfig` holds a single `AI_MODEL` field (a
`provider/model` string, e.g. `gemini/gemini-3.6-flash` — set via `task
setup`'s two-step provider→model picker, done in Phase 2) plus
`DISPLAY_STRING`/`DISPLAY_COLORS` for CLI rendering.

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
`taskai.cli.execute_commands`, one call per entry). Both call
`litellm.completion(model=model_name, messages=[...])` — provider-agnostic
per the `AI_MODEL` config value, no more hardcoded Gemini/`google-genai`.
See [taskai/llm_models.py](taskai/llm_models.py) for the provider→env-var
and provider→model reference data `task setup` uses. The natural-language prompt embeds
[taskai/help_menu.py](taskai/help_menu.py)'s `help_general` string as the
LLM's command reference — **that file is the single source of truth for the
command surface, shown to humans via `task help` and to the LLM verbatim.
Keep it in sync with `execute_commands` whenever the command set changes**,
it's gone stale before.

**Known code quirks (found but intentionally not fixed — out of scope
unless you're told to fix them):**
- ~~`Controller.update_item` (`cli.py`) resolves a non-numeric `item_id` via
  `_find_model_by_stringmatch` but assigns the *whole model object* back
  into `item_id` instead of pulling `.id` off it~~ **Fixed.** All identifier
  resolution (id or name) now routes through one function,
  `Controller._resolve_item()` (throws via `throw_error` if not found; a
  non-throwing `_find_item_by_identifier` still backs the soft-fail `show`
  path). Every command that takes an item identifier — `update`, `rename`,
  `status`, `done`/`complete`, `comment`, `depend`, `reorder`, `move`,
  `link`, `delete`, `create`'s parent — now accepts a name via `fnmatch`,
  not just a numeric id. Net effect was less code, not more: two
  name-only-duplicate methods (`show_by_item_name`, `delete_item_by_name`)
  and several inline `_is_int(...)` dispatch branches in `execute_commands`
  were deleted outright rather than kept alongside the id path.
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
- **Sync is one-directional: CLI → browser only, not the reverse.**
  `GET /api/tree` (`browser.py`) reloads from disk (`db.flush()`) on every
  call, and `canvas.js` refetches on window focus, so browser-side views
  pick up CLI edits made while the tab was in the background. But a running
  `task` interactive session holds its own in-memory `db.user_data` loaded
  once at startup — it has no equivalent reload/refetch, so an edit made in
  the browser (edit panel or console) isn't visible there until you kill and
  restart the interactive session. Acceptable for now; the real fix is the
  planned move to a daemonic backend thread/process with the CLI as a client
  the same way the browser already is, not a patch on the current
  per-process-connects-once model.

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

Two entry points, built in stages, not one replacing the other:
**`task ai <prompt>`** (2.1-2.3 below) is the existing one-shot flow —
model sees the prompt once, returns a full JSON list of commands up front,
they execute with no gating, same as today just on `litellm`. **`task ai
agent <prompt>`** (2.4, later) is a separate, more elaborate entry point for
multi-step workflows using a real tool-calling loop, added only after 2.1-2.3
are working and any kinks (context injection, multi-file support) are worked
out on the simpler path first.

### 2.1 — `task ai <prompt>` on `litellm` (no gating, same one-shot shape as today)

- [x] Depended on the Phase 0 fixes (prompt bug, `_add_info` bug, actually
      executing parsed commands) — done.
- [x] Originally planned on `aisuite` (below was written for it), but
      pivoted after reading `aisuite`'s actual provider source: its only
      Google provider is Vertex AI (`GOOGLE_PROJECT_ID`/`GOOGLE_REGION`/a
      service-account JSON) — no path to a plain Gemini/AI-Studio API key,
      which is what the existing setup actually used. `litellm` has a
      separate `gemini` provider (distinct from its own `vertex_ai`) that
      reads `GEMINI_API_KEY` directly, so the simple-API-key setup carries
      over unchanged. Added `litellm>=1.98` to `pyproject.toml`; dropped
      `google-genai` and the `from google import genai` import from
      `services/ai.py`.
- [x] Swapped both call sites (`ai_headstart_service`,
      `ai_natural_language_service`) to
      `litellm.completion(model=model_name, messages=[...])`, reading
      `response.choices[0].message.content`.
      **Scope note:** plain chat completions only, no `tools=`. The model
      still returns one JSON list of `{command, args, kwargs}` up front,
      same shape/contract as today, executed through `execute_commands`
      with no confirmation step — that's deliberate for this pass, not an
      oversight. The tool-calling loop is 2.4, later, not here. Model
      strings are `provider/model` (litellm's separator, e.g.
      `gemini/gemini-3.6-flash`, `openai/gpt-4o-mini`).
- [x] `litellm` reads provider credentials from standard provider env vars
      (`OPENAI_API_KEY`, `GEMINI_API_KEY`, etc.), not a key passed in.
      Dropped the `@config("GEMINI_API_KEY", "api_key")` plumbing entirely —
      one less thing to configure and one less place a secret sits in the
      plaintext user JSON db.
- [x] Renamed `CLIConfig.GEMINI_MODEL`/`GEMINI_API_KEY` to a single
      `AI_MODEL` field holding the `provider/model` string.
- [x] Kept printing the parsed command list before executing it
      (`print(response_json)`) — cheap safety net given the parsed commands
      can include `delete`/`nuke`. Still just visibility, not a confirmation
      prompt — real gating is what 2.4 adds.

### 2.2 — Context injection (`--context`), including the multi-file kink

- [x] `--context <path1,path2,...>` on `task ai <prompt>`: comma-separated
      as planned (sidesteps the `_parse_remaining` repeated-flag kink
      entirely — never needed to touch it). `_read_context_files()` in
      `services/ai.py` reads each file and folds them into the prompt as
      `--- <path> ---\n<contents>` sections, inserted between the item tree
      and the user's actual prompt.
- [x] Real landmine found while wiring this up, not in the original plan:
      `execute_commands`'s `case "ai":` dispatch built the prompt string
      from `args[1:]` but never forwarded `**kwargs` to
      `Controller.ai_natural_language` at all — any `--flag` on `task ai
      ...` was silently parsed and then dropped on the floor before
      `--context` even had a chance to matter. Fixed by forwarding
      `**kwargs` through the `case "ai":` dispatch and having
      `Controller.ai_natural_language` (`cli.py`) and
      `ai_natural_language_service` (`services/ai.py`) both accept it
      explicitly. A missing/misspelled path just raises `FileNotFoundError`
      naturally, caught by `execute_commands`'s existing catch-all — no new
      error handling needed.
- [x] Documented `--context` (and `--reasoning`, below) under `task ai` in
      `help_menu.py`, which is also the AI's own command reference — this
      command doesn't affect what the LLM is allowed to emit (it's a
      human-only flag on the `ai` invocation itself, not a command the
      model generates), but the doc was out of sync with reality otherwise.

**Also added, not originally scoped:** `--reasoning <level>` on `task ai
<prompt>`, passed straight through as `reasoning_effort` on the
`litellm.completion(...)` call — came out of a discussion about `task ai`
latency. Accepted values (`minimal|low|medium|high|disable|none`) aren't
validated client-side; an invalid value raises litellm's own
`Invalid reasoning effort: <value>` error, which already surfaces cleanly
through the same catch-all. No default is set — omitting the flag means no
`reasoning_effort` is sent at all, so behavior is whatever the model/provider
defaults to. (A `"disable"` default was tried and explicitly reverted this
session — worth knowing if it comes up again.) Confirmed by reading
litellm's Gemini transformation source directly: on Gemini 2.5-series models
this maps to a `thinkingBudget` token count and `"none"` genuinely zeroes
it out, but on Gemini 3.x (the default in `llm_models.py`'s menu) it maps
to a `thinkingLevel` enum and litellm's own code comment states Gemini 3
*cannot* fully disable thinking — `"disable"`/`"none"` just fall back to
the minimum level. Also gated behind `supports_reasoning(model, ...)`
internally, so it's silently a no-op (or may error) on non-reasoning tiers
like Flash-Lite.

### 2.3 — Update setup script for `litellm`

- [x] `services/user_setup.py` reworked into a two-step picker: select a
      provider, then select a model, both via a numbered-menu-or-free-text
      prompt (`_select_from_list`) — typing a number picks from the menu,
      typing anything else is taken literally, so a stale/missing menu entry
      never blocks you. Combines to `AI_MODEL = "<provider>/<model>"` and
      prints the exact env var(s) that provider needs.
- [x] New [taskai/llm_models.py](taskai/llm_models.py) (top-level, not
      under `services/`, since it's reference data, not a service):
      `PROVIDER_ENV_VARS` and `PROVIDER_MODELS`, both keyed by litellm's
      real provider names, pulled from `litellm.types.utils.LlmProviders`
      and `litellm.utils.validate_environment` directly rather than
      guessed. `PROVIDER_MODELS` is a non-exhaustive, best-effort menu —
      model names go stale fast, confirmed live mid-session: the `gemini`
      entries needed a web-search correction after `gemini-2.0-flash`
      turned out to have been shut down 2026-06-01 and `gemini-3.6-flash`
      didn't exist yet in training data. Re-verify against
      https://ai.google.dev/gemini-api/docs/models if `task setup`'s Gemini
      options look off again.
- [x] Updated README's Config section to match the new `AI_MODEL`
      `provider/model` shape and point at `task setup`.

### 2.4 — `task ai agent <prompt>` (later — real tool-calling loop)

A separate entry point, not a replacement for `task ai`. `task ai <prompt>`
stays the fast, ungated, one-shot-plan-and-execute path from 2.1-2.3;
`task ai agent <prompt>` is for workflows where the model actually needs to
see intermediate results (e.g. the real id of an item it just created)
before deciding the next step, which a one-shot plan can't do.

**Note (post-litellm-pivot):** this section was originally scoped around
`aisuite`'s automatic tool-runner (`tools=[...]` + `max_turns`, which drives
the call → execute → feed-result-back loop for you). `litellm.completion`
also accepts `tools=[...]` (OpenAI-style function-calling schema) but has no
automatic multi-turn runner — the loop below would need to be hand-rolled.
Re-scope this section before starting 2.4.

- [ ] Small, explicitly-typed wrapper functions — one per meaningful
      command (create, update, complete, delete, comment, depend, link,
      move; roughly 8-12 total, not one-per-every-CLI-verb) — calling
      straight into the existing `Controller` methods, exposed as
      `tools=[...]` to `litellm.completion`.
- [ ] Hand-roll the call → execute → feed-result-back loop (no automatic
      runner in `litellm`, unlike the originally-planned `aisuite`), capped
      at some max number of turns.
- [ ] Gate destructive tools (`delete`, `nuke`) behind an explicit yes/no
      confirmation before executing — not just the print-before-execute
      visibility 2.1 has.
- [ ] Print/log the tool-call transcript as it runs so the agent shows its
      work — same spirit as 2.1's visibility bullet, scaled to a multi-step
      run.
- [ ] Flagged, not scoped yet: multi-turn memory across calls in one
      session, a per-call `--model` override, streaming for plain-text
      responses (`headstart`). Revisit after 2.4 ships if still wanted.

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
