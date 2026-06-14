# standard lib
import os
from pathlib import Path
import shutil

# local
from taskai.models import *

# external
import orjson as json

class JsonDirectoryDatabase:

    def __init__(
            self,
            dirpath: os.PathLike,
            user: str
    ):
        
        self.db_dir = Path(dirpath)
        self.user_name = user
        self.user_data_path = Path(dirpath) / (user.strip(" ") + ".json")
        self.user_data = None

        if not os.path.exists(self.db_dir):
            self._setup_directory()
        
        if not os.path.exists(self.user_data_path):
            self._setup_user_data()
    
    def remove(self):
        if os.path.exists(self.db_dir):
            shutil.rmtree(self.db_dir)

    # setup utils
    def _setup_directory(self):
        os.makedirs(self.db_dir, exist_ok=True)

    def _setup_user_data(self):
        user_data = User(
            id="0",
            name=self.user_name
        ).model_dump()

        user_data[TodoList.__name__] = {}
        user_data[TodoItem.__name__] = {}
        user_data[Comment.__name__] = {}
        user_data["config"] = {}

        self.user_data = user_data
        self.commit()

    # data accessors
    @property
    def lists(self) -> dict:
        return self.user_data[TodoList.__name__]    
    
    @property
    def items(self) -> dict:
        return self.user_data[TodoItem.__name__]

    @property
    def comments(self) -> dict:
        return self.user_data[Comment.__name__]
    
    @property
    def user_id(self):
        return self.user_data["id"]
    
    @property
    def config(self) -> dict:
        return self.user_data["config"]

    # io
    def connect(self):
        with open(self.user_data_path, "rb") as f:
            json_bstring = f.read()
            self.user_data = json.loads(json_bstring)

    def commit(self):
        with open(self.user_data_path, "wb") as f:
            json_bstring = json.dumps(self.user_data)
            f.write(json_bstring)
    
    def flush(self):
        self.user_data = None
    
    def close(self):
        self.flush()
    
    # crud
    def create(self, record: Base) -> int:

        record.id = str(self.user_data["id_counter"])
        record.user_id = self.user_id

        if isinstance(record, TodoList):
            self.lists[record.id] = record.model_dump()

        elif isinstance(record, TodoItem):
            self.items[record.id] = record.model_dump()
            self.lists[record.list_id]["item_ids"].append(record.id)
        
        elif isinstance(record, Comment):
            self.comments[record.id] = record.model_dump()
            self.items[record.item_id]["comment_ids"].append(record.id)
        else:
            raise RuntimeError("don't know what you're creating")
        
        self.user_data["id_counter"] += 1
        return record.id
    
    def read(self, id_: int|str) -> Base:
        id_ = str(id_)
        if id_ in self.user_data[TodoList.__name__]:
            return TodoList(**self.lists[id_])
        elif id_ in self.user_data[TodoItem.__name__]:
            return TodoItem(**self.items[id_])
        elif id_ in self.user_data[Comment.__name__]:
            return Comment(**self.comments[id_])
        else:
            raise RuntimeError("Can't find record to read")

    def update(self, record: Base) -> None:
            
        if isinstance(record, TodoItem):

            assert record.id in self.items, "item doesn't exist"
            
            # update dependencies
            old_item: TodoItem = self.items[record.id]
            if old_item["list_id"] != record.list_id:
                old_list: TodoList = self.read(old_item["list_id"])
                old_list.item_ids.remove(record.id)
                new_list: TodoList = self.read(record.list_id)
                new_list.item_ids.append(record.id)

            self.items[record.id] = record.model_dump()
        
        elif isinstance(record, TodoList):
            assert record.id in self.lists, "list doesn't exist"
            old_list: TodoList = self.lists[record.id]
            for item_id in old_list["item_ids"]:
                if item_id not in record.item_ids:
                    self.items.pop(item_id)
            self.lists[record.id] = record.model_dump()

        else:
            raise RuntimeError("don't know what you're updating")
        
    def delete(self, id_: int|str) -> None:
        id_ = str(id_)
        if id_ in self.user_data[TodoList.__name__]:
            list_: TodoList = TodoList(**self.lists.pop(id_))
            for item_id in list_.item_ids:
                self.items.pop(item_id)
        elif id_ in self.user_data[TodoItem.__name__]:
            item: TodoItem = TodoItem(**self.items.pop(id_))
            self.lists[item.list_id]["item_ids"].remove(id_)
        elif id_ in self.user_data[Comment.__name__]:
            comment: Comment = Comment(**self.comments.pop(id_))
            self.items[comment.item_id].comment_ids.remove(id_)
        else:
            raise RuntimeError("Don't know what you're deleting")
    

    # Utilities
    def get_list_by_name(self, name: str):
        for list_id in self.lists:
            list_: TodoList = self.read(list_id)
            if list_.name.lower() == name.lower():
                return list_
        raise RuntimeError("Don't recognize list")


    # Config
    def get_config_value(self, key: str) -> any:
        return self.user_data["config"].get(key)

    def get_config(self) -> dict:
        return self.user_data.get("config", {})

    def set_config_value(self, key: str, value: any):
        self.user_data["config"][key] = value