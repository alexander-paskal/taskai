class TaskCLIError(Exception):
    """Raised by Controller.throw_error for any user-facing command failure.

    A real Exception subclass (not sys.exit's SystemExit) so it can be
    caught by ordinary `except Exception` handlers - notably the
    interactive REPL loop, which needs to survive a bad command rather
    than have the whole process torn down by an uncatchable SystemExit.
    """
    pass
