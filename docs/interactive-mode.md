# Interactive mode

Run `task` with no arguments to enter interactive mode:

```bash
task
```

The screen clears and shows your full tree, followed by a prompt:

```text
Type your commands:
```

Enter any command exactly as you would on the command line, without the leading
`task` (though `task ...` is accepted too). After each command the screen
redraws with the updated tree.

- A `show` command sets the view that stays on screen — `task show "Launch
  blog"` keeps that subtree visible as you keep working; `show all` goes back to
  the whole tree.
- Every other command runs, then the view refreshes.
- Leave with `exit`, `quit`, or Ctrl-C.
