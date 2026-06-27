import argparse
import orjson as json
from taskai.models import TodoItem

def migrate(data):
    if "TodoList" in data:
        for k, record in data["TodoList"].items():

            record["child_ids"] = record.pop("item_ids")
            TodoItem(**record)
            print(f"Converting {k} to Item")
            data["TodoItem"][k] = record
        data.pop("TodoList")

    for k, record in data["TodoItem"].items():

        if "title" in record:
            print(f"converting title->name for {k}")
            record["title"] = record["name"]
            record.pop("title")

        if "parent" in record:
            print(f"converting parent->parent_id for {k}")
            record["parent_id"] = record["parent"]
            record.pop("parent")
    
        if "child_ids" not in record:
            print(f"Adding Child IDs {k}")
            record["child_ids"] = []
        
        try:
            data["TodoItem"][k] = TodoItem(**record).model_dump()
        except:
            print("validation for {} failed".format(k))
            import sys
            sys.exit()


arg_parser = argparse.ArgumentParser()
arg_parser.add_argument("path", help="path to taskai root")
args = arg_parser.parse_args()

with open(args.path, "rb") as f:
    data = json.loads(f.read())

migrate(data)


with open(args.path, "wb") as f:
    f.write(json.dumps(data))
