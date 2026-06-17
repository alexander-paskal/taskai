import argparse
import orjson as json


def convert_name_to_name(path):
    with open(path, "rb") as f:
        data = json.loads(f.read())

    for k, record in data["TodoItem"].items():

        if "name" in record:
            print(f"migrating {k}")
            record["name"] = record["name"]
            record.pop("name")
        elif "name" in record:
            print(f"validated {k}")
        else:
            print(f"{k} is corrupted")
    
    with open(path, "wb") as f:
        f.write(json.dumps(data))


arg_parser = argparse.ArgumentParser()
arg_parser.add_argument("path", help="path to taskai root")
args = arg_parser.parse_args()


convert_name_to_name(args.path)

