import sys
import os
import tomlkit

projdir = os.path.dirname(os.path.dirname(__file__))
with open(os.path.join(projdir, "pyproject.toml")) as f:
    toml = tomlkit.load(f)

major, minor, bugfix = list(map(int, toml["project"]["version"].split(".")))

args = sys.argv[1:]

if not args:
    bugfix += 1
elif args[0] == "bugfix":
    bugfix += 1
elif args[0] == "minor":
    minor += 1
    bugfix = 0
elif args[0] == "major":
    major += 1
    minor = 0
    bugfix = 0
else:
    print("didn't work")
    print(args)
    sys.exit(-1)

new_version = f"{major}.{minor}.{bugfix}"
print("Bumping to version {}".format(new_version))
toml["project"]["version"] = new_version


with open(os.path.join(projdir, "pyproject.toml"), "w") as f:
    tomlkit.dump(toml, f)


