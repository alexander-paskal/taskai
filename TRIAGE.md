# TRIAGE

Backlog from the CLI deep-dive audit (see DEVLOG 8-24), triaged by severity.
Items 1-3 from the original audit (the `SystemExit`-kills-the-session bug,
`task repair` being fully broken, and `task nuke` leaving the db unusable +
having no confirmation) are already fixed — not listed here. Everything
below is still open. Work through top to bottom within a tier; tier order
is the priority order.

---

## Critical

- [x] **Fixed.** ~~Name-based item lookup can silently resolve to the wrong
      item.~~ `Controller._find_model_by_stringmatch` (`cli.py`) no longer
      inverts `{id: name}` into `{name: id}` (which silently dropped all but
      one id whenever two items shared a name). It now iterates
      `batch_attrs.items()` directly, `fnmatch`-matching each name and
      collecting *every* matching id. Exactly one match resolves as before;
      zero matches still returns `None` (soft-fail for `show`, hard error via
      `_resolve_item` for mutating commands); **two or more matches now call
      `throw_error`** listing the colliding ids and telling the user to refer
      to the item by id. Turns the silent wrong-item edit/delete into an
      explicit, actionable error. (Note: the outer
      `for record_type in [TodoItem, Comment]` loop is still dead — comments
      have no `name` and `get_item_batch_attr` only reads `todo_items` —
      tracked separately under Low / "Dead code in
      `_find_model_by_stringmatch`".)

---

## High

- [ ] **`create`/`add`/`rename` silently truncate unquoted multi-word
      input; `comment` crashes on it instead — and `task ai headstart` has
      the same underlying problem.** See the walkthrough from this session
      for the full trace — short version: `create`/`add`/`rename` only
      ever read a single token (`args[1]`/`args[2]`) for a field that's
      conceptually free text, silently dropping everything after the
      first word if you don't quote it; `comment` spreads all remaining
      words into `create_comment(item_id, content)`, which only accepts
      two positional args, so it throws a `TypeError` instead. `task ai
      headstart <prompt>` is the same class of bug from the other
      direction: `ai_headstart(item_id)` only accepts one positional arg,
      but `case "headstart":` passes `*args[2:]`, so any prompt with more
      than one word after "headstart" (e.g. `task ai headstart the
      report`) throws a `TypeError` — even though the user very plausibly
      meant a natural-language prompt that happens to start with that
      word, not the `headstart` subcommand at all.
      **Open design question, not just a mechanical fix:** for `create` and
      `rename`, joining the trailing args (like `task ai` already does) is
      unambiguous — there's exactly one free-text field and nothing after
      it. For `add {parent} {name}`, it's not that simple: the parent
      comes *first*, so if the parent identifier is also given unquoted
      and multi-word, there's no way to tell where the parent reference
      ends and the item name begins just by splitting on spaces.
      `headstart` has a version of the same problem: how many leading
      words are the id/name argument vs. the start of a natural-language
      prompt? Needs a decision before implementing — e.g. always require
      the parent/id argument to be quoted/a single token and join
      everything after it as the free-text field. `create` and `rename`
      can proceed independently of resolving this.
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

---

## Low

- [x] **Fixed.** ~~`task delete completed`/`done` can never target an item
      literally named "completed"/"done".~~ Removed `delete completed`/
      `delete done` outright rather than disambiguating — `task clear`
      already does the exact same thing (and with no argument, clears
      everywhere), so the two were redundant. `delete` now always treats
      its argument as an item identifier.
- [x] **Fixed.** ~~No `unlink`.~~ Added `task unlink {parent} {item}` —
      `Controller.remove_link` (`cli.py`) mirrors `add_link`: resolves both
      identifiers, `throw_error`s if the link isn't actually present, else
      removes `child.id` from `parent.linked_ids` and commits. Dispatched
      via a `case "unlink":` next to `case "link":`, documented in
      `help_menu.py` next to `task link`. (The `update <id> --linked_ids`
      path still doesn't work — that's the separate `_parse_item_kwargs`
      quirk in DEVPLAN, untouched.)
- [x] **Fixed.** ~~`task show <id1>,<id2>,...` is documented but not wired
      up.~~ Removed rather than wired up — `Controller.show_items` and
      `view_items` (`views.py`) deleted entirely, and the README's line for
      it removed. `task show` only ever takes one target now.
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
