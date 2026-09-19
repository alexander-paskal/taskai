# demo.gif recording script

Production note for whoever records `docs/_static/demo.gif` — not a
published page (this directory is Sphinx's static-asset folder, copied
as-is, never parsed as content). Delete this file once the real gif is in
place and this is no longer needed.

**Target:** ~20-30s, terminal only (a separate, shorter browser-mode clip
can live on its own if wanted — this one is the CLI). Readable font size,
nothing that requires the viewer to have already read the docs.

Run this in a scratch directory with a fresh `.taskai/task_db` (`task nuke`
first if reusing one, or just start somewhere new) so item ids are small
and the tree is uncluttered.

```bash
task create "Launch blog"
task add "Launch blog" "Write outline" --priority 1 --due tomorrow
task next "Write outline" "Draft intro"
task show all
task done "Write outline"
task ai "add a task under Launch blog to buy a domain"
task show all
```

What this covers, in order:
1. `create`/`add` — the everything-is-an-item tree, with a couple of fields
   set (`--priority`, `--due tomorrow` — also shows off the relative
   date keyword)
2. `next` — chains, the newest major feature, right after the tree basics
3. `show all` — the Rich-rendered tree, chain included (rendered inline
   with the bold down-arrow between chain links)
4. `done` — quick, satisfying, worth the second of screen time
5. `task ai` — the natural-language layer actually creating something,
   then a final `show all` so the viewer sees its result land in the tree

Skip `task browser` here — screen-recording a pannable/zoomable canvas
doesn't compress well as a small looping gif, and it already gets its own
screenshots (see the placeholders in `docs/browser-mode.md`).
