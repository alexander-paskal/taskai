from taskai.cli import execute_commands


commands = [
    dict(args=(), kwargs={}),

]


if __name__ == "__main__":
    for c in commands:
        execute_commands(*c["args"], **c["kwargs"])