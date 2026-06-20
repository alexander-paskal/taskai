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
            self._validate_parentage(kwargs["parent_id"], item.id)

        return item.id
        
    def create_comment(self, content: str, item_id: int, **kwargs) -> int:
        comment = Comment(content=content, item_id=item_id, **kwargs)
        comment.id = self._get_new_id()
        
        # create comment
        self._debug(f"Creating comment {comment.id}")
        self.user_data.comments[str(comment.id)] = comment.model_dump()

        # update item
        self._validate_comment(comment.id, comment.item_id)

        return comment.id
        
    def delete_item(self, id: int) -> bool:
        if str(id) not in self.user_data.todo_items:
            raise DatabaseError(f"No record by id {id}")
        parent_id = self.get_item_attr(id, "parent_id")
        self._debug(f"Deleting item {id}")
        item_dict = self.user_data.todo_items.pop(str(id))
        self._validate_parentage(parent_id, id)
        # recursively delete children
        for child_id in item_dict["child_ids"]:
            self.delete_item(child_id)

    def delete_comment(self, id: int) -> bool:
        if str(id) not in self.user_data.comments:
            raise DatabaseError(f"No record by id {id}")
        comment = self.get_comment(id)
        self._debug(f"Deleting comment {id}")
        self.user_data.comments.pop(str(id))
        self._validate_parentage(comment.id, comment.item_id)    
    
    def update_item(self, id: int, **kwargs) -> bool:
        if str(id) not in self.user_data.todo_items:
            raise DatabaseError(f"No record by id {id}")
        # validate the full new item
        item_dict = self.user_data.todo_items[str(id)].copy()
        item_dict.update(kwargs)
        new_item_dict = TodoItem(**item_dict).model_dump()

        if new_item_dict["parent_id"]:
            self._validate_parentage(new_item_dict["parent_id"], id)

        self._debug(f"Updating item {id}")
        self.user_data.todo_items[str(id)] = new_item_dict

    def update_comment(self, id: int, **kwargs) -> bool:
        if str(id) not in self.user_data.comments:
            raise DatabaseError(f"No record by id {id}")
        # validate the full new item
        comment_dict = self.user_data.todo_items[str(id)].copy()
        comment_dict.update(kwargs)
        new_comment_dict = Comment(**comment_dict).model_dump()
        self._validate_comment(id, new_comment_dict["child_id"])
        self._debug(f"Updating comments {id}")
        self.user_data.comments[str(id)] = new_comment_dict

    def update_config(self, **kwargs) -> bool:
        config_dict = self.user_data.config.copy()
        config_dict.update(kwargs)
        self._debug(f"Updating config {id}")
        new_config_dict = CLIConfig(**config_dict).model_dump()
        self.user_data.config = new_config_dict

    def _validate_comment(self, comment_id: int, item_id: int):
        item_exists = str(item_id) in self.user_data.todo_items
        comment_exists = str(comment_id) in self.user_data.comments

        match (item_exists, comment_exists):
            case (True, True):  # make sure they reference each other
                comment = self.get_comment(comment_id)
                comment_ids = self.get_item_attr(item_id, "comment_ids")

                # make sure the item references the comment in its comment list
                if comment_id not in comment_ids:
                    self._debug(f"Adding comment {comment_id} to item {item_id}")
                    comment_ids.append(comment_id)
                    self.update_item(item_id, comment_ids=comment_ids)

                # make sure the comment references its parent
                if comment.item_id != item_id:
                    self._debug(f"Setting comment {comment_id} to reference item {item_id}")
                    self.update_item(comment_id, item_id=item_id)
            
            case (False, True):  # delete the comment if its parent is deceesed
                self._debug(f"Deleting orphan comment {comment_id}")
                self.user_data.comments.pop(str(comment_id))
            
            case (True, False):  # remove the comment id from the item's list of comments
                comment_ids =  self.get_item_attr(item_id, "comment_ids")
                if comment_id in comment_ids:
                    self._debug(f"Removing reference to comment {comment_id} from item {item_id}")
                    comment_ids.remove(comment_id)
                    self.update_item(item_id, child_ids=comment_ids)
            
            case (False, False):
                self._debug(f"Couldn't find reference to comment {comment_id} or item {item_id}")    

    def _validate_parentage(self, parent_id: int, child_id: int):
        parent_exists = str(parent_id) in self.user_data.todo_items
        child_exists = str(child_id) in self.user_data.todo_items

        match (parent_exists, child_exists):
            case (True, True):  # make sure they reference each other
                child = self.get_item(child_id)
                parent_children_ids = self.get_item_attr(parent_id, "child_ids")
                
                # make sure the child id is in the parent's children list
                if child_id not in parent_children_ids:
                    self._debug(f"Adding child {child_id} to parent {parent_id}")
                    parent_children_ids.append(child_id)
                    self.update_item(parent_id, child_ids=parent_children_ids)

                # make sure the child references the parent
                if child.parent_id != parent_id:
                    self._debug(f"Setting child {child_id} to reference parent {parent_id}")
                    self.update_item(child_id, parent_id=parent_id)
            
            case (False, True):  # set child parent_id to null
                self._debug(f"Setting child {child_id} as root")
                self.update_item(child_id, parent_id=None)
            
            case (True, False):  # remove the child id from the parents list
                parent_children_ids=  self.get_item_attr(parent_id, "child_ids")
                if child_id in parent_children_ids:
                    self._debug(f"Removing reference to child {child_id} from parent {parent_id}")
                    parent_children_ids.remove(child_id)
                    self.update_item(parent_id, child_ids=parent_children_ids)
            
            case (False, False):
                self._debug(f"Couldn't find reference to child {child_id} or parent {parent_id}")
                

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
