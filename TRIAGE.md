# TRIAGE

Backlog from the CLI deep-dive audit (see DEVLOG 8-24), triaged by severity.
Items 1-3 from the original audit (the `SystemExit`-kills-the-session bug,
`task repair` being fully broken, and `task nuke` leaving the db unusable +
having no confirmation) are already fixed — not listed here. Everything
below is still open. Work through top to bottom within a tier; tier order
is the priority order.

---

## Critical

- [ ] **Name-based item lookup can silently resolve to the wrong item.**
      `Controller._find_model_by_stringmatch` (`cli.py`) inverts an
      `{id: name}` dict into `{name: id}` before matching:
      ```python
      inside_out = {v: k for k, v in batch_attrs.items()}  # TODO this is hacky
      results = fnmatch.filter(batch_attrs.values(), pattern)
      if results:
          id_ = inside_out[results[0]]  # might be duplication
      ```
      Inverting the dict silently drops all but one id whenever two items
      share the same name — the one that survives is whichever happened to
      be last in iteration order, not necessarily the one you'd expect.
      Item names aren't required to be unique anywhere in the model, so
      this is reachable any time you have two same-named items (e.g. two
      subtasks both named "Notes" under different parents) and refer to
      one by name in `update`/`delete`/`move`/etc. — no error, just a
      silent edit/delete of the wrong item. Worth fixing before anything
      else on this list because it's the only item here with no visible
      symptom at all.

---

## High

- [ ] **`create`/`add`/`rename` silently truncate unquoted multi-word
      input; `comment` crashes on it instead.** See the walkthrough from
      this session for the full trace — short version: `create`/`add`/
      `rename` only ever read a single token (`args[1]`/`args[2]`) for a
      field that's conceptually free text, silently dropping everything
      after the first word if you don't quote it; `comment` spreads all
      remaining words into `create_comment(item_id, content)`, which only
      accepts two positional args, so it throws a `TypeError` instead.
      **Open design question, not just a mechanical fix:** for `create` and
      `rename`, joining the trailing args (like `task ai` already does) is
      unambiguous — there's exactly one free-text field and nothing after
      it. For `add {parent} {name}`, it's not that simple: the parent
      comes *first*, so if the parent identifier is also given unquoted
      and multi-word, there's no way to tell where the parent reference
      ends and the item name begins just by splitting on spaces. Needs a
      decision before implementing — e.g. always require the parent to be
      quoted/a single token (id or exact single-word name) and join
      everything after it as the name, or something else. `create` and
      `rename` can proceed independently of resolving this.
- [x] **Fixed.** **`task config pop <key>` is broken for every key**, and `config
      set`/`config get` fail silently or crash on a bad key.
      `remove_config_value` (`cli.py`) does:
      ```python
      def remove_config_value(key: str):
          db.update_config(**{key: None})
      ```
      No `CLIConfig` field (`models.py`) is actually `Optional` — even
      `AI_MODEL: str = None` is typed plain `str` despite its `None`
      default — so writing `None` through fails pydantic validation every
      time. Real fix is conceptual: `pop` should remove the key from the
      stored config dict so the field falls back to its own pydantic
      default, not null it out. `config set`/`get` also don't validate the
      key exists before using it — a typo'd key on `set` prints a false
      "success" message with zero effect (pydantic silently drops unknown
      keys), and on `get` throws an `AttributeError`.
- [ ] **`task ai headstart <multi-word prompt>` crashes** instead of
      falling through to natural language. `ai_headstart(item_id)` only
      accepts one positional arg, but `case "headstart":` passes
      `*args[2:]` — any prompt with more than one word after "headstart"
      (e.g. `task ai headstart the report`) throws a `TypeError`, even
      though the user very plausibly meant a natural-language prompt that
      happens to start with that word.

---

## Low

- [x] **Fixed.** ~~`task delete completed`/`done` can never target an item
      literally named "completed"/"done".~~ Removed `delete completed`/
      `delete done` outright rather than disambiguating — `task clear`
      already does the exact same thing (and with no argument, clears
      everywhere), so the two were redundant. `delete` now always treats
      its argument as an item identifier.
- [ ] **`depend` allows duplicate entries.** `add_dependency` unconditionally
      appends to `dependency_ids` with no dedup check, unlike `add_link`
      (which already guards `if child.id not in parent.linked_ids`).
      Running `task depend 5 6` twice gives `dependency_ids = [6, 6]`.
- [ ] **No `undepend`/`unlink`.** Once a dependency or link is added,
      there's no CLI path to remove it — `update <id> --dependency_ids ...`
      doesn't work either, since `update_item` never calls
      `_parse_item_kwargs` (separately known/tracked in DEVPLAN's "known
      code quirks").
- [ ] **`task show <id1>,<id2>,...` is documented but not wired up.**
      README documents it and the implementation
      (`Controller.show_items`/`view_items`) already exists and works —
      `execute_commands`'s `show` case just never dispatches to it.
- [ ] **`task browser` is undocumented and has no `[port]` option.** Not
      mentioned anywhere in `help_menu.py`, so it's undiscoverable short of
      reading source. `Controller.browser_service` hardcodes uvicorn's
      default port with no override, despite DEVPLAN's original Phase 1.1
      scoping a `task web [port]`.
- [ ] **`examples`/`show examples` are two redundant dead ends.** Both
      route to the same unimplemented `show_examples()`, which just prints
      `"Not implemented yet"` — not documented in help_menu either. Either
      implement it once or delete both entry points.
- [ ] **Dead code in `_find_model_by_stringmatch`.** Beyond the Critical
      item above, the function also loops over `[TodoItem, Comment]`
      intending to fall back to searching comments by name, but
      `db.get_item_batch_attr(attr)` only ever reads `todo_items` — the
      second loop iteration just re-runs the identical lookup. Comments
      don't even have a `name` field, so the premise doesn't apply. Marked
      in the code itself as `# TODO this is hacky`.
