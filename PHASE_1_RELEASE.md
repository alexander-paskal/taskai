# Phase 1 Release — Punch List

All the major features for v1 are done (browser DAG with chains, `task ai`
on `litellm`, filters, comments, keyboard shortcuts, the chain CLI). This is
what's left before cutting the release — pulled from the open items in
[DEVPLAN.md](DEVPLAN.md) and [TRIAGE.md](TRIAGE.md) plus new scope Alex
added directly to this list, filtered down to what's actually in scope for
"ready to ship v1," not the longer-term roadmap. Real new features
(dependency edges in the DAG, `task ai agent`, a fully expanded `task show`
view) are called out at the bottom as explicitly **not** v1 — they're
staying in DEVPLAN/TRIAGE, not duplicated here.

---

## Small polish

- [x] **`task browser` has no `[port]` override.** (TRIAGE / Low)
      `Controller.browser_service` hardcodes uvicorn's default port.
      Original DEVPLAN scoping (1.1) called for `task web [port]`; small,
      contained fix. `task browser {port}`, defaults to 8000.
- [x] **DAG empty/loading state.** (DEVPLAN Phase 3) A user with no tasks
      yet just sees a blank canvas — no "nothing here yet" state. Drawn in
      screen space (stays centered regardless of pan/zoom) whenever
      `graph.nodes.length === 0` — covers both "still loading" and
      "genuinely empty" with one message rather than adding a separate
      loading-flag/spinner for what's normally a near-instant local fetch.
- [x] **`style.css` spacing/typography consistency pass.** (DEVPLAN Phase 3)
      Never done; low effort, worth a once-over before screenshots go in
      the docs/listing. Pulled the repeated color/font literals (border,
      muted/primary/label text, accent blue, input background, both font
      stacks — each duplicated 2-9x) into `:root` custom properties;
      normalized the one real inconsistency found, an odd `12.5px` body
      text size next to `13px` used everywhere else for the same kind of
      text. Deliberately left spacing/radius values (8/10/6/5px) alone —
      those read as intentionally graduated by element scale, not
      erroneous, and I can't visually verify a change without screenshots.
- [x] **Re-check the Phase 0 fixes are still holding.** (DEVPLAN Phase 3)
      Written when the web UI was new; now that chains + the new CLI
      surface exercise a lot more of `execute_commands`, worth a quick
      re-pass rather than assuming. All 5 confirmed intact via source
      inspection: `ai_prompt` (not the raw prompt) is what's sent to the
      LLM; `_add_info`'s visited-set bug stays fixed; the parsed command
      list from `task ai` is actually executed
      (`services/ai.py`'s loop over `execute_commands`); `execute_commands`'s
      except block has no `raise e` ahead of the friendly `throw_error`
      path; `views.py` no longer calls the nonexistent `db.read`/`db.items`.
      No live LLM call made (didn't want to spend API quota for this) —
      everything else checked statically.
- [x] **Delete should shift focus intelligently, not just to the root.**
      After deleting the selected node, restore selection to whatever was
      focused *before* it (needs at least a one-deep "previously selected"
      memory, since `state.selectedNode` today just gets re-resolved to
      `rootNode` once the deleted id no longer exists in the fresh graph)
      — fall back to the synthetic root only if there's nothing to return
      to. `state.previousSelectedId` (canvas.js), updated by `selectNode`
      any time the selection actually changes — so this falls out of the
      same general mechanism for every navigation, not something
      delete-specific.
- [x] **`next` should focus the node it just created.** Today, running
      `next <prev> <name>` through the console applies the fresh tree but
      doesn't select/focus anything — you have to go find it. `show`
      already gets special server-side `focus`-id handling in
      `POST /api/command` (`taskai/browser.py`); extending that same
      `focus` response to `next` (the newly-appended item's id) is the
      consistent way to do this, rather than a client-side before/after-id
      diff like `addNodeAndEdit`'s shortcut does for `a`. Server-side:
      diffs `db.get_item_ids()` before/after running `next` through
      `execute_commands`. Found and fixed a related inconsistency in
      passing: the console's *generic* command fallback (any command not
      specially handled, like `next` typed directly) was already reading
      `data.focus` and moving the camera, but never actually calling
      `selectNode` — so it centered on the new node without selecting it
      (edit panel wouldn't update, arrow nav wouldn't be relative to it).
      Fixed to call both.
- [x] **Show `due_by` on the node itself.** `render.js`'s `drawNode` draws
      id (top-left) and `status` (top-right) already; add `due_by`
      somewhere on the card (needs a spot picked that doesn't collide with
      the wrapped label or the status text). Landed bottom-right,
      compact `MM/DD`. Had to add `due_by` to `graph.js`'s node object too
      — it wasn't being copied from the API payload at all.

## New features for v1

- [x] **Configuration needs to actually reach the browser.** `STYLE` in
      `config.js` is hardcoded JS — the file's own header comment already
      says "this will eventually be served by a backend endpoint (e.g.
      `GET /api/style`)." This is the foundational piece the next two items
      ride on: a config surface (new `CLIConfig` keys, most likely) that
      the browser reads at load, rather than everything being a compile-time
      JS constant. New `GET /api/style` (`browser.py`) returns the raw
      `CLIConfig.model_dump()` unprocessed — no new endpoint needed every
      time a renderer-relevant key gets added later, interpreting it is
      each consumer's own job. Frontend: `canvas.js`'s new `loadConfig()`
      fetches it into `STYLE.serverConfig` before the first tree load
      (`loadConfig().then(loadTree)`, so config is guaranteed to be in
      place before the first real render); `config.js` seeds
      `STYLE.serverConfig = {}` so nothing has to null-check before that
      resolves. Verified: `curl /api/style` against a live instance
      returns the real `CLIConfig` JSON. No visible UI change from this
      commit alone by design — nothing reads `serverConfig` yet, the next
      item is the first real consumer.
- [x] **Node render color as an item attribute.** A per-item color override
      (new `TodoItem` field, or reuse an existing free-form one) that
      `render.js`'s `drawNode` checks before falling back to the
      completed/default fill — lets a user color-code specific nodes
      directly rather than only via `completed`/`status`. New `TodoItem.
      color: Optional[str]` (any CSS color string), threaded through
      `graph.js`'s node object and checked in `drawNode` before the
      completed/default fill logic. Edit panel gets a plain text field
      (deliberately not a native `<input type="color">` — that widget can
      never represent "unset," always some valid hex color; an empty
      string here correctly falls back to the default via JS truthiness,
      no special-case handling needed anywhere). Verified end to end:
      created an item with `--color`, confirmed it in the live `/api/tree`
      payload, cleared it back to `""` and confirmed the model round-trips
      that correctly.
- [x] **Status-string → color mapping, defined in config.** e.g.
      `RUNNING=green, BLOCKED=red` as a new `CLIConfig` key (config-key
      naming and exact syntax TBD — something in the spirit of the existing
      `DISPLAY_STRING`/`DISPLAY_COLORS` pair). Right now every non-empty
      `status` renders the same fixed orange in the DAG (`STYLE.colors.
      statusText`) regardless of its value; this makes that configurable
      per status string. Depends on the config-to-browser item above.
      New `CLIConfig.STATUS_COLORS: str = ""`, comma-separated
      `STATUS=color` pairs (e.g. `"RUNNING=green,BLOCKED=red"`) — settable
      with the existing generic `task config set STATUS_COLORS ...`, no new
      command needed. `render.js`'s new `parseStatusColors` parses it once
      into `STYLE.statusColors` (in `canvas.js`'s `loadConfig`); `drawNode`
      looks up the node's exact `status` string there before falling back
      to the fixed `statusText` color. Verified: unit-tested the parser
      (whitespace, multiple pairs, empty/undefined input) and round-tripped
      a real value through `task config set` → `GET /api/style` against a
      live instance.
- [x] **Chain-aware up/down arrows when there's no conflicting tree
      relationship.** Currently arrows are pure tree nav and `f`/`b` are
      the only way to walk a chain (deliberate split — see DEVPLAN 1.8,
      worked out after hitting the "is c1 a chain head or a tree parent"
      ambiguity). Refinement: a chain member's real children and its chain
      successor/predecessor are mutually exclusive to check *per
      direction*, so there's no actual ambiguity in the cases below —
      - `down`: if the node has real children, behave exactly as today
        (descend into them). **Only if it has none**, fall back to
        `chainNext` instead of dead-ending.
      - `up`: if the node has a tree parent, behave exactly as today.
        **Only if it doesn't** (true for every non-head chain member,
        which never has one), fall back to `chainPrev`.
      This only changes behavior in the "otherwise a dead end" case — a
      node with both a real child and a chain link (e.g. a chain head with
      its own children) keeps today's behavior exactly, `f`/`b` still work
      everywhere unchanged. Verified against 7 cases covering both
      fallbacks, both non-fallback (unchanged) paths, and the true dead end
      (tail, down).
- [x] **Transpose the DAG's coordinate axes: growth goes right, spread goes
      down** (today: growth down, spread right). Affects `measure`/`place`
      in `graph.js` — swap which recursion axis feeds `marginX +
      ...*xSpacing` vs. `marginY + ...*ySpacing` in `place()`, done
      consistently for both the classic tree layout and the chain layout
      (a chain currently drawn "straight down, children to the right"
      would become "straight right, children downward" — same relationship,
      rotated). **Open question to settle when this is picked up:** should
      the arrow-key mapping rotate with it (right arrow = descend, down
      arrow = next sibling) so the keys still feel spatially consistent
      with what's on screen? Leaning yes, but worth confirming rather than
      assuming. **Went with yes.** Turned out to be a genuinely small,
      contained change: `place()`'s two recursion parameters were already
      abstract ("spread" and "growth" in grid units) — every call site
      below the top two lines passes them straight through unchanged, so
      the *entire* orientation is decided in exactly those two lines
      (renamed the parameters from `x`/`y` to `spread`/`growth` so that's
      obvious on read, not just true by convention). Also had to fix:
      `treeGap`'s unit conversion (was dividing by `xSpacing`, needs
      `ySpacing` now that it's a spread-axis gap); the synthetic
      `rootNode`'s position (was "above the roots," now "before them along
      growth," centered on spread); `focusOnNode`'s off-center bias
      (renamed `STYLE.zoom.focusYRatio` → `focusGrowthRatio`, moved from Y
      to X); and `navigation.js`'s depth-level grouping for left/right
      (was "shared y sorted by x," now "shared x sorted by y"). Console
      text commands (`up`/`down`/`left`/`right`) and `f`/`b` keep their
      original *structural* meaning unchanged (typing "down" always means
      "my child," regardless of screen orientation) — only the *physical*
      arrow-key → structural-direction mapping in `shortcuts.js` rotates
      (`ArrowRight`→"down", `ArrowLeft`→"up", `ArrowDown`→"right",
      `ArrowUp`→"left"). `Shift`+arrow panning stays tied to the actual
      screen direction, untouched. Verified: rebuilt the graph from real
      chain data and confirmed growth increases along X while chain
      members/side-children/siblings spread along Y; confirmed
      `navigateGraph`'s rotated depth-level stepping against that same
      layout; confirmed every static file still serves against a live
      `task browser` instance.
- [x] **Smarter `due_by` parsing.** Two related asks:
      - **Format inference.** `_parse_item_kwargs` (`cli.py`) currently
        hard-requires `MM-DD-YYYY` (`datetime.strptime(v, "%m-%d-%Y")`) —
        anything else throws. Accept common formats without the user
        needing to know the exact one (ISO `YYYY-MM-DD`, `MM/DD/YYYY`,
        `Dec 31 2026`, etc.) — likely a small ordered list of formats tried
        in turn, or a light date-parsing library if one's already
        available/acceptable to add as a dependency.
      - **Relative keywords.** `due_by=today` / `due_by=tomorrow` (that's
        filter syntax — `taskai/filters.py`'s `due_by<op>value` — so this
        reads as primarily a filters ask: `task show 'due_by<today'` etc.
        Worth deciding at implementation time whether the same keywords
        should also work on the *setting* path — `--due_by tomorrow` on
        `create`/`add`/`update`/`next` — since both go through date
        parsing but currently via different code (`filters.py` vs.
        `_parse_item_kwargs`) and only one was explicitly asked for.
      **Resolved: did both, via one shared helper.** New
      [taskai/dates.py](taskai/dates.py), `parse_date_value(raw)` — tries a
      list of formats (`MM-DD-YYYY`, ISO, `MM/DD/YYYY`, `MM/DD/YY`, and
      `Month D[,] YYYY` in long/short-month variants) then falls back to
      `today`/`tomorrow` (case-insensitive). Used by *both*
      `_parse_item_kwargs`'s `due_by` branch (`cli.py`) and
      `filters.py`'s `_coerce` for `due_by`/`created_on` — so
      `--due_by tomorrow` on `create`/`add`/`update`/`next` and
      `task show 'due_by=today'` both work, not just one. Verified: the 7
      existing tests still pass; unit-checked every format + both
      keywords + a bad-input error path directly; end-to-end through the
      real CLI (`create --due_by 2026-12-25`, `update --due_by tomorrow`,
      `show 'due_by=tomorrow'` all resolved and matched correctly).
      `help_menu.py` updated in both spots (item-fields table and the
      filter example line).

## Docs

- [ ] Replace `docs/_static/demo.gif` placeholder with a real recording —
      referenced from `index.md` and the README.
- [ ] Confirm the Read the Docs project slug (`conf.py`'s `html_baseurl` +
      README currently assume `taskai`).
- [ ] Screenshots for browser-mode docs.
- [x] `help_menu.py`/README are current as of the chain work (Phase 8) —
      spot-check the RTD site's generated pages didn't drift now that
      `help_general` has a new "Chains:" section (`docs/commands.md`
      `literalinclude`s it automatically, but worth a build-and-look). Ran
      `sphinx-build -b html docs docs/_build/html`: builds clean (1
      pre-existing warning, the known `demo.gif` placeholder — unrelated),
      and the built `commands.html` correctly includes the full "Chains:"
      section verbatim. Nothing needed fixing.
- [ ] Lower priority, nice-to-have if time allows: explanation/architecture
      pages, custom 404, OpenGraph cards, CI `linkcheck`, a changelog.

## Testing

- [x] **Zero test coverage for the chain feature.** The most structurally
      risky thing shipping in this release (`next`/`chain`/`unchain`,
      `delete -chain`, chain-aware `clear`, the `insert_node_into_chain` /
      `remove_node_from_chain` / `delete_chain` DB methods) currently has no
      tests at all — worth prioritizing over the general suite-broadening
      below given how much subtle pointer-juggling is in that code path.
      New [test/test_chains.py](test/test_chains.py), 12 DB-layer tests
      covering insert (builds exactly one head; detaches a node already
      mid-chain before re-splicing it elsewhere, verifying *both* chains
      end up clean; pops a node off a real tree parent; inserting into the
      middle of an existing chain), remove (middle-link relink; tail
      shortening; head removal both standalone — the old head legitimately
      stays put, matching what `unchain` needs — and via `delete_item`,
      where it doesn't, which is the actual regression test for the
      chain-head-deletion bug; the length-2-chain collapse edge case), and
      `delete_chain`/`delete_item` interplay (full cascade + parent
      detachment; a chain nested under a deleted parent takes its
      real-children cascade path too; a plain mid-chain `delete` still
      behaves like a linked-list splice). Also added a CLI-dispatch smoke
      test to `test_cli.py` (`test_run_chain_commands`) exercising
      `next`/`chain`/`unchain`/`delete -chain` end to end through the real
      `execute_commands` path, matching the existing suite's
      subprocess-based style. **Found one real bug writing these**, caught
      by the test suite itself: my first draft of the head-removal test
      called `remove_node_from_chain` directly and asserted the old head
      was gone from the parent's children — wrong assertion, not a code
      bug (that function alone never deletes anything, `delete_item` does,
      by calling `remove_child_from_parent` *before* it) — but chasing it
      down is exactly the kind of thing this coverage was for. All 20 tests
      pass (7 pre-existing + 13 new).
- [ ] Broaden the general test suite (DEVPLAN Phase 6) — currently 7 tests
      total across `test_cli.py`/`test_execution.py`/
      `test_json_dir_database.py`/`test_view.py`. Lower priority than the
      chain coverage above for a v1 cutoff specifically.
- [ ] Wire CI (`pytest` on every PR, `sphinx-build -W` + `linkcheck` for
      docs) — nice-to-have, fine to slip past v1 if time is tight.

---

## Explicitly NOT v1 (stays in DEVPLAN/TRIAGE, not duplicated here)

- **`dependency_ids`** — Alex's call: drop this from v1 scope entirely,
  revisit as a Phase 2 issue (whether that means wiring up `depend`/
  `undepend` or actually removing the dead field stays an open question for
  then, not now).
- **`task show` — light polish only for v1, full expansion later.**
  DEVPLAN Phase 5 already flags the expanded view (depth limits, flat vs.
  tree, sort order, color toggles) as needing a scoping session; Alex
  confirmed: keep v1's touch light, scope the bigger version collaboratively
  when picked up.
- Dependency edges in the browser DAG, and a real `depend`/`undepend` UI —
  deferred to "2.0" in DEVPLAN 1.4/2.4 (same field as above).
- `task ai agent <prompt>` (real tool-calling loop, gated destructive
  actions) — deferred to "2.0" in DEVPLAN 2.4.
- Advertising/launch prep (DEVPLAN Phase 7) — a separate workstream from
  code readiness, not a polish/bugfix item.
- DEVPLAN Phase 1.1's originally-planned stdlib `http.server` + `task web
  [port]` module is stale — the real implementation is FastAPI + uvicorn via
  `taskai/browser.py`, built out completely under 1.2–1.8. Not a real to-do;
  DEVPLAN should probably strike that subsection out rather than leave it
  looking open.
