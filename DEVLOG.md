# 8-22

Found and fixed a real bug from the `litellm` migration earlier today: it
auto-loads `.env` via `python-dotenv` on import, and the project's `.env`
had a stray first line (`source .taskai-venv/bin/activate` — not a
`KEY=VALUE` pair), so every `task ai` run printed a "could not parse
statement starting at line 1" warning. Non-fatal (`GEMINI_API_KEY` on line
2 still loaded fine) but confusing. Diagnosed by reading `litellm/__init__.py`
directly rather than guessing — it calls `_dotenv.load_dotenv(...)` at
import time. Left the actual `.env` edit to Alex since it holds a live key.

Also stripped two leftover debug `print()`s from `ai_natural_language_service`
(the raw prompt and the full constructed `ai_prompt` — fine for iterating on
the prompt, noise now that this is a user-facing command) and reworked the
"about to run these commands" printout: instead of one `print(response_json)`
dump of the raw parsed list, it now prints each command right before running
it, reconstructed as `ai run 'task <command> ...'` (quoting only values with
spaces) via a small `_format_command_str()` helper — reads like a real
command instead of a dict dump, and shows progress as it goes rather than
front-loading everything.

Added `--context` and `--reasoning` to `task ai <prompt>` (DEVPLAN 2.2,
below, has the durable version of this):

- `--context a.md,b.md` reads file(s) and folds them into the prompt.
- While wiring it up, found `execute_commands`'s `case "ai":` dispatch
  never forwarded `**kwargs` to `Controller.ai_natural_language` at all —
  `--context` would've parsed fine and then been silently dropped before
  reaching the service. Fixed by threading `**kwargs` through the whole
  chain (`cli.py`'s dispatch → `Controller.ai_natural_language` →
  `ai_natural_language_service`).
- `--reasoning <level>` came out of a tangent about `task ai` latency: Alex
  asked whether "respond quickly" in the prompt does anything (no — output
  token generation is sequential/autoregressive, prompt wording can't speed
  that up) and what actually causes it. Real answer: some Gemini tiers
  generate a hidden "thinking" pass before the visible output, which is a
  genuine invisible latency cost. Read litellm's Gemini transformation
  source directly to confirm the actual knob: `reasoning_effort` is a
  standard litellm kwarg on `completion()`, mapped per-provider — accepts
  `minimal|low|medium|high|disable|none`. Confirmed a real wrinkle for this
  project specifically: on Gemini 2.5-series models it maps to a
  `thinkingBudget` token count and `"none"` zeroes it out completely, but
  on Gemini 3.x (what `llm_models.py`'s menu defaults to) it maps to a
  `thinkingLevel` enum, and litellm's own code comment says Gemini 3
  *cannot* fully disable thinking — `"disable"`/`"none"` just fall back to
  the minimum level there. Only exposed for reasoning-capable tiers
  (`supports_reasoning(...)` gated internally), so it may no-op or error on
  something like Flash-Lite.
- Tried defaulting `--reasoning` to `"disable"` when omitted, then Alex
  reverted that — omitting the flag now sends no `reasoning_effort` at all,
  leaving it up to whatever the model/provider defaults to.
- Documented both flags under `task ai` in `help_menu.py` (this file is
  also the AI's own command reference, so it needs to stay accurate even
  though neither flag is something the model itself would ever emit).

---

Migrated AI backend off direct `google-genai` calls, landing on `litellm`
after a detour through `aisuite`:

- First tried `aisuite` per DEVPLAN's original Phase 2 plan. Downloaded and
  read the actual package source before committing to it (not just docs) —
  found `aisuite`'s only Google provider is Vertex AI
  (`GOOGLE_PROJECT_ID`/`GOOGLE_REGION`/a service-account JSON), with no path
  to a plain Gemini/AI-Studio API key. Since the existing setup is just a
  simple API key, that would've been a real functionality change disguised
  as a library swap. Flagged it to Alex before writing any code.
- Alex opted to rework the setup rather than force-fit the old flow, but
  then asked whether another compat layer supported plain Gemini API keys —
  it does: `litellm` treats `gemini` and `vertex_ai` as separate providers
  (confirmed by reading `litellm/utils.py`'s `validate_environment` and
  `litellm/types/utils.py`'s `LlmProviders` enum directly), so
  `gemini/<model>` + `GEMINI_API_KEY` keeps the current simple setup working
  end to end. Redid the migration against `litellm` instead.
- `pyproject.toml`: `google-genai` → `litellm>=1.98`.
- `taskai/models.py`: `CLIConfig.GEMINI_MODEL`/`GEMINI_API_KEY` collapsed to
  a single `AI_MODEL: str` (a `provider/model` string, litellm's own
  separator).
- `taskai/services/ai.py`: both `ai_headstart_service` and
  `ai_natural_language_service` now call
  `litellm.completion(model=model_name, messages=[...])` instead of
  `google.genai`; dropped the `api_key`/`@config("GEMINI_API_KEY", ...)`
  plumbing since litellm reads provider credentials straight from env vars.
- New [taskai/llm_models.py](taskai/llm_models.py) (top-level, not under
  `services/` — it's reference data, not a service): `PROVIDER_ENV_VARS`
  (which env var(s) litellm expects per provider) and `PROVIDER_MODELS` (a
  best-effort, non-exhaustive menu of known models per provider). Both
  built by reading litellm's source directly rather than guessing.
- `services/user_setup.py` reworked into a two-step picker
  (`_select_from_list`): pick a provider from a numbered menu, then pick a
  model for that provider from another numbered menu. Either step also
  accepts free-typed text instead of a number, so a stale/missing
  `PROVIDER_MODELS` entry (several providers — `azure`, `ollama` — are
  intentionally empty, since their "models" are a deployment name or
  whatever you've pulled locally) never blocks setup.
- Caught a live example of "models go stale fast" mid-session: Alex hit
  `gemini-3.6-flash` referenced by Google's own tooling, which wasn't in
  training data. Web-searched Google's current model docs and corrected the
  `gemini`/`vertex_ai` entries in `llm_models.py` — `gemini-2.0-flash` (the
  old hardcoded default) was actually shut down 2026-06-01. If `task
  setup`'s Gemini options look wrong again, re-check against
  https://ai.google.dev/gemini-api/docs/models rather than trusting the
  hardcoded list.
- README's Config section updated to match (`AI_MODEL` as `provider/model`,
  points at `task setup`).
- Not yet done: `pip install "litellm>=1.98"` / `pip uninstall google-genai`
  in `.taskai-venv` — Alex needs to run this manually (environment-mutating
  commands aren't run unprompted in this project).

DEVPLAN.md's Phase 2 (2.1, 2.3) updated to match — checked off, `aisuite`
references swapped for `litellm`, and 2.4 (the later tool-calling-loop
entry point) flagged for re-scoping since it was written around `aisuite`'s
automatic tool-runner, which `litellm` has no equivalent for.

---

# 8-19

Fixed a typo in `browser.py` that caused uvicorn to fail with "Could not import
module 'taskai.browser'" when launching on a new machine: `os.path.dirname(__file)`
should have been `__file__` (double underscores). The `NameError` was raised at
module import time before FastAPI could even get the app object.

Added three console QoL commands, handled entirely client-side (no server round-trip):

- `zoom in` / `zoom out` — zoom ×1.5/÷1.5 around the canvas center
- `pan left` / `pan right` / `pan up` / `pan down` — shift viewport 250px per step

Implemented as `easeView` / `canvasZoom` / `canvasPan` helpers in `canvas.js`
(same ease-out cubic as `focusOnNode`), with a `CLIENT_COMMANDS` dispatch map in
`console.js` that intercepts matching input before it reaches the fetch path.

Added `edit <id|name>` console command: resolves the target via the existing
`show` server path (reuses `_find_item_by_identifier`, so fnmatch patterns work),
then selects the node, focuses/zooms the canvas to it, and expands the edit panel.
Added `openEditPanel()` to `editpanel.js` for this purpose.

---

# 8-18

Continued the browser/`canvas.js` work in a later session (DEVLOG is a
stack now — newest first within a date — so this sits above the earlier
entries from today):

- Console got wired up for real: `POST /api/command` now exists in
  `browser.py` (design: branch on whether the parsed command is `show` —
  `show` never touches `execute_commands`, it's read-only from the
  browser's perspective, it just resolves a target id and returns it as
  `focus` for the frontend to `focusOnNode` on; everything else runs
  through `execute_commands` with stdout captured, always returning the
  fresh full tree). Found a real landmine while building it:
  `Controller.throw_error` calls `sys.exit(-1)`, raising `SystemExit`,
  which `execute_commands`'s own `except Exception` doesn't catch — any
  bad console command would've thrown that straight through the request
  handler. Caught at the server boundary only, `cli.py` untouched. Console
  input now actually POSTs, echoes output, and applies the returned tree.
- Node labels now wrap up to 3 lines before truncating (was single-line
  truncate only) — `wrapText` in `canvas.js`, refactored `fitText`'s
  trimming logic into a shared `truncateWithEllipsis` helper.
- `completed` items get a soft green fill/border
  (`STYLE.colors.nodeFill/BorderDone`). Each node also shows its id
  (top-left, small muted gray) and, when set, its `status` (top-right,
  small warm orange, ellipsis-truncated if it'd collide with the id).
- Tuned double-click focus after it read as too aggressive: scale down
  1.4 → 0.85 (settles slightly zoomed *out*, not in), and it no longer
  centers vertically — lands at 20% down from the top
  (`STYLE.zoom.focusYRatio`) so there's room below to see a focused node's
  children.
- Built the edit panel (right-side, collapsible, `editpanel.js` +
  `.edit-panel` in `style.css`): collapsed is just a bare `44px` chevron
  button pinned to its own top-left corner (no visible bar), expanded is a
  `320px` white panel. Toggling animates the canvas's width/pan/zoom in
  step with the panel's own 200ms CSS transition (`setRightPanelWidth` in
  `canvas.js`), rescaling zoom in proportion to the width change (not just
  re-panning) so the same amount of graph stays in view instead of getting
  cropped. This required adding real click-to-select on the DAG first
  (`selectedNode` in `canvas.js`, persistent blue border, re-resolved by
  id after every tree refresh so it doesn't silently dangle) — the edit
  panel piggybacks off that selection.
- Edit panel form: `name`, `description`, `status`, `priority`, `due_by`,
  `completed`, `dependency_ids` ("Depends on"), each typed to match its
  data (text/textarea/number/date/checkbox). No Save button — deliberate:
  every field POSTs `update <id> --<field> <value>` to `/api/command`
  directly. Checkbox sends immediately; everything else debounces 1s per
  field (keyed by item+field) so typing doesn't spam a request per
  keystroke.
- Confirmed against a throwaway test item (created + deleted, not real
  data) that `name`/`description`/`priority`/`completed` all update
  correctly end to end. `due_by` and `depends_on` don't — both trace to
  `Controller.update_item` never calling `_parse_item_kwargs` the way
  `create_item` does, so `due_by` throws a validation error and
  `depends_on` silently no-ops. Documented in DEVPLAN's known quirks,
  left unfixed on purpose (explicit call: wire the endpoint first, fix
  bugs later).

Phase 1 status per the updated DEVPLAN checklist: only dependency/link
edges (1.4) and console up-arrow history (1.6) remain open. Everything
else in Phase 1 — tree render, pan/zoom, click-to-select, completed/status
display, the command endpoint, the edit panel, the console — is done.

---

Working with Claude this session. Started a DEVPLAN.md with a roadmap
(Phase 0: bugfixes, Phase 1: browser UI, Phase 2: AI/aisuite rewrite,
Phase 3: polish) plus ground rules for how we want to work together.

Phase 0 (bugfixes), done:
- ai.py: the natural-language prompt was being built (with the command
  grammar + task tree baked in) but the actual LLM call sent the raw
  un-instructed prompt instead - fixed.
- ai.py: `_add_info` (used to build the task-tree context for the AI
  prompt) referenced the wrong loop variable and would throw on the first
  recursive call - fixed.
- ai.py: the natural-language service parsed the LLM's JSON command list
  but never actually ran it - now it executes each parsed command through
  `execute_commands`, same dispatcher the CLI uses.
- cli.py: `execute_commands` had a `raise e` ahead of the friendly
  `throw_error` path, so errors always came out as raw tracebacks - removed.
- views.py: `view_item`/`view_items` called `db.read`/`db.items`, which
  don't exist on `JsonDirectoryDatabase` - fixed to `get_item`/
  `get_item_ids`. Also found and fixed a second bug on the same path:
  `view_items` was passing the whole `TodoItem` object into `view_item`
  instead of its `.id`.

Also did a pass on help_menu.py and the AI prompt in ai.py:
- help_menu.py's command reference was stale (referenced commands/syntax
  that don't exist, missing others that do) - rewrote it to match
  `execute_commands` exactly, including which commands need an id vs.
  accept a name, and the `--field` table that wasn't documented anywhere.
- Added explicit rules to the AI prompt about not referencing items that
  don't exist yet (create it first), preferring ids over names for the
  commands that need them, and not inventing commands/fields.
- Removed "list" as a separate concept from both docs - it's a generic
  item tree now. Clarified `create` = new root item, `add` = child of an
  *existing* parent only.

Found (not fixed, tracked in DEVPLAN's "known quirks"): `update_item`
resolves a name to a model object but never unwraps `.id` before handing
it to the db layer, so `update`/`rename`/`status` only work with numeric
ids, not names.

Browser phase, started on the `browser` branch:
Already had FastAPI + uvicorn wired up (`task browser` -> launches
uvicorn on taskai.browser:app) and a canvas.js proof-of-concept
(hardcoded fake tree, circle nodes, click/hover hit-testing) from an
earlier session. Decided to build on that instead of the stdlib
http.server + SVG that DEVPLAN originally sketched, since it already ran
end to end. Wired it to real data:
- browser.py: added `GET /api/tree`, reusing the db connection already
  established by importing `taskai.cli` (no second connection).
- canvas.js: replaced the hardcoded fake tree with `loadTree()`, which
  fetches `/api/tree`, builds the real node tree from `parent_id`/
  `child_ids`, and lays it out with a simple depth-first layout (y from
  depth, x from a running leaf counter, parents centered over children).
  Handles a forest of root items, not just a single root.
- Verified end to end against the real dev database.

Still open for Phase 1: the `/api/command` mutation endpoint, the edit
menu, the console panel, dependency/link edges, pan/zoom, node coloring.
Nothing there yet beyond the read-only tree render.

DEVPLAN.md now has a full "Project overview" section prepended (data
model, storage, CLI dispatch, known quirks, dev environment, etc.) so a
fresh session doesn't need to re-derive all of this by reading the whole
codebase. Also added a ground rule to keep this DEVLOG updated going
forward.

Kept going on the DAG view (`canvas.js`) in the same session, testing
live against `task browser` running throughout:
- Labels no longer overflow the node: truncated with an ellipsis to fit,
  full label shown in a tooltip on hover. Hover also now visibly
  highlights the node — previously tracked but had no effect.
- Added pan (drag) and zoom (wheel, zooms toward the cursor) via a `view`
  {offsetX, offsetY, scale} object and canvas context transforms, not SVG
  `viewBox` — same reasoning as the earlier canvas-not-SVG call. A drag
  past a small threshold suppresses the trailing click so panning across
  a node doesn't also fire its click handler.
- Added double-click a node to ease the view to center + zoom on it
  (`focusOnNode`, ease-out cubic, ~250ms). Note: this is *not* the edit
  menu trigger — double-click is now spoken for by center/zoom, so 1.5's
  edit menu will open off a single-click "selected node" instead (that
  selection state doesn't exist yet; today click only `console.log`s).
- Reworked the whole visual style: nodes went from small fixed circles to
  much larger rounded squares (currently 160 world units), sized so
  normal-length labels fit without truncating. Pulled every visual knob
  (colors, node size/shape/font, spacing, zoom bounds, tooltip) out into
  a `STYLE` config object at the top of `canvas.js` — deliberately plain
  data, no functions, so it can later be swapped for a `GET /api/style`
  response instead of hardcoded constants. Went through two style passes
  with Alex: first a dark "sleek/modern" theme, then a full swap to a
  TickTick-inspired light theme (off-white canvas, flat white node cards,
  soft low-opacity shadow instead of a heavy one, blue accent on
  hover/select, system font stack). Also made the canvas fill the
  viewport (was a fixed 800x800 box) with a resize listener.
- Widened spacing to match the bigger nodes: sibling/parent-child spacing
  up from 90/100 to 230/230, plus a dedicated extra gap (`treeGap`, 260)
  inserted only *between* separate root trees in the forest, not between
  siblings within one tree. Zoom's lower bound dropped 0.2 → 0.1 so a
  bigger graph can still be zoomed out to fit; upper bound stayed at 4.

Still open for Phase 1, per the updated checklist in DEVPLAN.md: click-
to-select (persisted selection, needed before the edit menu can piggyback
off it), dependency/link edges, node coloring by status/completed, the
`/api/command` mutation endpoint, the edit menu itself, and the console
panel.

# 6-25

Alright let's start to think a bit about how I want to handle the pomo service.

task pomo 25 3


Let's start with spawning the timer, and then we can worry about logging and shit.

Pomo should spawn a process and write a log to a database. The process
should continuously monitor that log and see "am I active?"
  - if so, it keeps running
  - if not, we prompt the user for what they want to do?
    - rest/reset/cancel
do I need this to be serialized even? maybe not if I'm just starting - we can start pomo in another thread (or just the same thread)

Yeah let's honestly not even worry about the multiprocessing part of it right now. 

Let's just enter a loop and count down, while I keep clearing the screen

I need to figure out how to make it play a bell or have a screen pop up (if it's running in the background)

# 6-20

Let's think critically about what i want this API to lookk like. How should be people be
using the CLI?


task create {name} {**kwargs} -> create an item
task add {parent_id} ...  -> create an item as a child
task show all
task show {id}



# 6-19

Really this whole thing should just be a tree abstraction, and I should have a root node class
and just built a tree database with some attrs depending on the type

idk why i'm being a dipshit
But that's gonna be the next iteration

# 6-18

Everything is fucked up anyways lol so might as qweell make some decisions about
the best way to do the database



```python
class DB:

    def get_item(id: int) -> TodoItem:
    def get_comment(id: int) -> Comment:
    def get_config() -> CLIConfig:
    def create_item(name: str, parent: Optional[TodoItem]=None, ...) -> str:
    def create_comment(content: str, parent: TodoItem) -> str:
    def delete_item(name: str) -> bool:
    def delete_comment(name: str) -> bool:
    def update_item(id_: int, kwargs) -> bool:
    def update_comment(id_: int, kwargs) -> bool:
    def update_config(kwargs) -> bool:

    def connect():
        pass
    def commit():
        pass
    def validate():
        pass

``` 

Important factors:
- do i want to serialize/deserialize every record twice? probably not
- so let's make sure that everything is read-only

How do i want to handle parentage? 
i could:
- do it at the client level i.e. make sure to call (add parent)
- do it at the db level i.e. on every create, update, and delete method, validate

Let's do it at the db level - i want the database to be responsible for ensuring data
validation so I don't have to worry about it when I'm writing code downstream


# 6-17

Alright I find myself needing to make some design decisions about hierarchical lists.

I could:
    - differentiate between child items and child lists, and have items only be leaf nodes
        pros:
        cons:
    - treat everything as a single "item" and simply due away with the concept of lists as a
      separate data point
    - still distinguish between the two but treat them all as child ids - useful for sorting

Looking at it, i see no good reason to distinguish between items and lists - it complicates the
code without adding any additional functionality. There is nothing that a list does that an item
can't do apart from be a container, and there's no reason why an item can't also be a container.

So let's just go ahead and implement that change. 


# 6-14

Damn it's been a productive couple of weeks. App is deployed on PyPi and I'm starting to think
a bit more about phase 2, how to rewrite it for ultimate success. What I'm thinking is that
things like help, argument patterns, and service logics should be bundled into one unit - 

the core infrastructure should basically load all of the services in the config, and pull their
argument pattern matching, help menus, etc. That way, the core of the app just works as a dispatcher

Things I need to have clearly in mind before I start rearchitecting:
- How i'm going to handle modularity and reuse for major components
- How i'm going to handle multiple threads and processes
    - a note on this - i'm leaning towards having a core metadata file that just keeps track
    of all processes, that we just read/write to (with some sort of locking mechanism). That
    will maintain process ids and any other shared state

But before all that good stuff, let's take what we have and polish the hell out of it


Also, as I'm doing this, it's becoming clear to me that I need to have records be a bit
more object oriented, as the number of different interactions that have to take place is 
getting more and more annoying to keep track of and the best place for everything to be
put would be as methods on the objects, i.e. "item.updateList()", etc.


# 6-3

Alright so how are comments gonna look here:

    ```
    Name:
    Due By:
    Description:
    Depends On:
    Comments

    ```


Let's think about what this cli refactor is gonna look like:


arg
    arg
        ...
            endpoint, *args, **kwargs



# 5-28

A couple things that I need to deal with:
- recursive deletes (so deleting hierarchical items)
- recursive completes
- better recurrence strategies
- how to deal with linking tasks that are recurrence of the same task
- database server

# 5-27

Let's think about this cli:

what do i want to be able to do?




- task add item|list|comment
- task show item|list|comment
- task complete {id}
- task delete {id}
- task {id} depends_on {id}
- task dependency_chain


- task {id} delete|done|show|edit


Let's start with some views

need to have recursive delete for lists

# 5-26

What can I build right now?

I want to have a basic CLI version of what I want. So we can use a pickle database,
define our models, and add the basic functionality to the core business logic. 


How can we design this?

- I could have a core app session that is built through some composition
- for different concurrent users, we could spin up different processes?
    - why don't I worry about scaling when it comes time to scale, let's just build osmething cool and useful right now

- So we have the app session object, and we can spin it up:
    - on startup
        - connect to a database
    - call methods to perform the actions we care about
        - commit changes as we want
        OR
        - have a plugin architecture where we can add views/operations that take in the session object
    - on exit

CLI version
    - do I want it to run in the background and communicate via pipes?
        - feels like that falls under premature optimization, maybe just try running everything at once to start
        - though that could be fun? maybe next start
    - maybe not a pickle database, can do a local folder json database



so:
    Session:
        def __init__(
            user: User,
            database: Database
        )

        def on_exit():
            ...

    cli/
        views/       --> views of the core data
        services/    --> core business operations we can perform
        cli.py





        





# 5-11

Alright let's think about backend

What is the point of this app? What do I want to be able to support?
- 



# 4-29

Alright let's think about frontend:

- Login Page:
     - Page 1: login
        - if logged in, show main
    
     - Main Page
        - SideBar
        - MainPanel
            - MainPanelOptions

            - TodoPanel
            - EditPanel
            - CanvasPanel


What I want to do:
- build the threads part
- build the login and user context part
- build the database backend interactions
- build the canvas part


How do I want to handle components?

Brainstorm:
- I could construct a component tree
    - each component could have a render call? Or just be called in its constructor, so when you instantiate
    it, it shows up
- I want to have statically defined models so that I don't have to reconstitute things (since that's a pain)



Alright yeah, components can also have a commit-esque method (although maybe that's case by case) where I
commit their data

In that sense, I don't even really need to predefine my HTML - I can just generate it on the fly and have my core
div structure be defined


So what would that look like?

<LoginForm>
<Main>
  <div> flex-col
  <TopPanel>
    
  <div> flex-row
      <SideBar>
      <TodoPanel>
      <EditPanel>
      <CanvasPanel>        

  <footer>



I can just have so many classes:
components/
  loginForm.js
  sidebar.js
  todopanel.js
  editpanel.js
  canvaspanel.js

lib/
  component.js
  database.js
  utils.js


Alright let's start to sketch these out:

We have our base:


    class Component extends HTMLComponent{

        db attribute
        state attribute

        constructor (
            super()
            const shadow = this.attachShadow({mode: 'open'})
            customElements.define(this.constructor.name, this.constructor)
        )
    }


    class LoginForm extends Component {
        constructor(
            super()




        )
    }











# 4-27


Alright sick progress, I'm in the process of populating the database. Now I need to:
- write the startup() method that pulls lists from the database and populates them in the sidebar
    ---> I'll put the populateDb method in there for now

- write the callback so that when I click on a list, it pulls its id from the database 
- write the rendering functions so that the todo-list-panel renders the todos for the selected list


# 4-26

What do I want to add?

Pages:
- login page
- Main Page


# Features that I want to add

- Pop Up Card Editing
- Comments
- Text CLI
- Dockerize
-  
