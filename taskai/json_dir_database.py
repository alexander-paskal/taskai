# standard lib
import os
from pathlib import Path
import shutil
from copy import copy
import dataclasses
from rich import print

# local
from taskai.models import *

# external
import orjson as json


class DatabaseError(Exception):
    pass


class JsonDirectoryDatabase:
    """
    All views extracted from the database are read only
    All updates should go through the database api
    The database is reponsible for ensuring a valid data model on every write
    """
    def __init__(
            self,
            dirpath: os.PathLike,
            user: str,
            debug: bool = False
    ):
        
        self.db_dir: Path = Path(dirpath)
        self.user_name: str = user
        self.user_data_path: Path = Path(dirpath) / (user.strip(" ") + ".json")
        self.user_data: UserData = None
        self.debug = debug

        if not os.path.exists(self.db_dir):
            self._setup_directory()
        
        if not os.path.exists(self.user_data_path):
            self._setup_user_data()
    
    # IO
    def connect(self):
        if self.user_data is None:
            with open(self.user_data_path, "rb") as f:
                json_bstring = f.read()
                if not json_bstring:  # zero length bstring
                    self.user_data = UserData(
                        name=self.user_name
                    )
                else:
                    self.user_data = UserData(**json.loads(json_bstring))
        else:
            raise DatabaseError("Database already connected")

    def commit(self):
        with open(self.user_data_path, "wb") as f:
            json_bstring = json.dumps(self.user_data.model_dump())
            f.write(json_bstring)
    
    def flush(self):
        self.close()
        self.connect()
    
    def close(self):
        self.user_data = None
    
    def remove(self):
        if os.path.exists(self.db_dir):
            shutil.rmtree(self.db_dir)

    # CRUD
    def get_item(self, id: int) -> TodoItem:
        try:
            return TodoItem(**self.user_data.todo_items[str(id)])
        except KeyError:
            raise DatabaseError(f"No record by id {id}")
    
    def get_items(self, ids: list[int]) -> list[TodoItem]:
        return [self.get_item(id) for id in ids]

    def get_item_ids(self) -> list[int]:
        return [int(k) for k in self.user_data.todo_items.keys()]

    def get_items_recursively(self, id, _existing_items: dict[int, TodoItem]=None) -> dict[int, TodoItem]:
        if _existing_items is None:
            _existing_items = {}
        _existing_items[id] = item = self.get_item(id)
        
        for child_id in item.child_ids:
            self.get_items_recursively(child_id, _existing_items=_existing_items)
        return _existing_items

    def get_item_attr(self, id: int, key: str) -> any:
        try:
            return copy(self.user_data.todo_items[str(id)][key]) 
        except KeyError:
            raise DatabaseError(f"No record by id {id}")
        
    def get_item_batch_attr(self, key: str) -> list[any]:
        return {
            id: self.get_item_attr(id, key) for id in self.get_item_ids()
        }
    
    def get_comment(self, id: int) -> Comment:
        try:
            return Comment(**self.user_data.comments[str(id)])
        except KeyError:
            raise DatabaseError(f"No record by id {id}")
    
    def get_config(self) -> CLIConfig:
        return CLIConfig(**self.user_data.config)
    
    def create_item(self, name: str, **kwargs) -> int:
        item = TodoItem(name=name, **kwargs)  # validate
        item.id = self._get_new_id()
        
        # create item
        self._debug(f"Creating item {item.id}")
        self.user_data.todo_items[str(item.id)] = item.model_dump()

        # update parent
        if kwargs.get("parent_id"):
            parent = self.get_item(kwargs["parent_id"])
            parent.child_ids.append(item.id)
            self._debug(f"Adding item {item.id} to parent {parent.id}")
            self.update_item(parent.id, child_ids=parent.child_ids)
        return item.id

    def create_comment(self, content: str, item_id: int, **kwargs) -> int:
        comment = Comment(content=content, item_id=item_id, **kwargs)
        comment.id = self._get_new_id()
        
        # create comment
        self._debug(f"Creating comment {comment.id}")
        self.user_data.comments[str(comment.id)] = comment.model_dump()

        # update item comment list
        item = self.get_item(item_id)
        item.comment_ids.append(comment.id)
        self.update_item(item.id, comment_ids=item.comment_ids)

        return comment.id

    def add_child_to_parent(self, child_id: int, parent_id: int):
        parent = self.get_item(parent_id)
        if child_id in parent.child_ids:
            raise DatabaseError(f"Item {child_id} already child of item {parent_id}") 
        parent.child_ids.append(child_id)
        self.update_item(parent.id, child_ids=parent.child_ids)
        self._debug(f"Adding item {child_id} to parent {parent.id}")

    def delete_item(self, id: int) -> bool:

        item = self.get_item(id)
        
        # recursively delete children
        for child_id in item.child_ids: 
            self.delete_item(child_id)

        # remove child from parent
        if item.parent_id is not None:
            self.remove_child_from_parent(item.id, item.parent_id)
        
        self._debug(f"Deleting item {id}")
        item_dict = self.user_data.todo_items.pop(str(id))

    def remove_child_from_parent(self, child_id: int, parent_id: int) -> bool:
        parent = self.get_item(parent_id)
        if child_id not in parent.child_ids:
            raise DatabaseError(f"Cannot delete child {child_id} from parent {parent_id}")
        parent.child_ids.remove(child_id)
        self.update_item(parent_id, child_ids=parent.child_ids)

    def delete_comment(self, id: int) -> bool:
        if str(id) not in self.user_data.comments:
            raise DatabaseError(f"No record by id {id}")
        comment = self.get_comment(id)
        self._debug(f"Deleting comment {id}")
        self.user_data.comments.pop(str(id))
    
        # TODO remove from parent
        item = self.get_item(comment.item_id)
        item.comment_ids.remove(id)
        self.update_item(item.id, comment_ids=item.comment_ids)

    def update_item(self, id: int, **kwargs) -> bool:
        if str(id) not in self.user_data.todo_items:
            raise DatabaseError(f"No record by id {id}")
        # validate the full new item
        old_item_dict = self.user_data.todo_items[str(id)].copy()
        old_item_dict.update(kwargs)
        new_item_dict = TodoItem(**old_item_dict).model_dump()

        self._debug(f"Updating item {id}")
        self.user_data.todo_items[str(id)] = new_item_dict

    def update_comment(self, id: int, **kwargs) -> bool:
        if str(id) not in self.user_data.comments:
            raise DatabaseError(f"No record by id {id}")
        # validate the full new item
        comment_dict = self.user_data.todo_items[str(id)].copy()
        comment_dict.update(kwargs)
        new_comment_dict = Comment(**comment_dict).model_dump()
        self._debug(f"Updating comments {id}")
        self.user_data.comments[str(id)] = new_comment_dict

    def update_config(self, **kwargs) -> bool:
        config_dict = self.user_data.config.copy()
        config_dict.update(kwargs)
        self._debug(f"Updating config {id}")
        new_config_dict = CLIConfig(**config_dict).model_dump()
        self.user_data.config = new_config_dict

    def get_config(self) -> CLIConfig:
        return CLIConfig(**self.user_data.config)
    
    # UTILS
    def _setup_directory(self):
        os.makedirs(self.db_dir, exist_ok=True)

    def _setup_user_data(self):
        user_data = UserData(
            id="0",
            name=self.user_name
        )
        self.user_data = user_data
        self.commit()
        self.close()
    
    def _get_new_id(self) -> int:
        self.user_data.id_counter += 1
        return self.user_data.id_counter

    def _debug(self, *args, **kwargs):
        if self.debug:
            print("db: ", *args, **kwargs)

    def _debug_print_tree(self):

        def _recursive_print(item, level):
            print("\t"*level + f"{item.id}-{item.name}" )
            for child_id in item.child_ids:
                child = self.get_item(child_id)
                _recursive_print(child, level+1)
        
        roots = [child for child in self.get_items(self.user_data.todo_items.keys()) if not child.parent_id]
        for root in roots:
            _recursive_print(root, 0)
