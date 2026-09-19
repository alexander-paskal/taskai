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


def _is_chain_head(item: TodoItem) -> bool:
    """A chain's head is the one member reachable from the tree (parent_id
    or a root) - everything after it is only reachable via next_chain_id."""
    return item.prev_chain_id is None and item.next_chain_id is not None


def _migrate_legacy_keys(user_data: UserData) -> None:
    """Backwards compatibility for data written before `due_by` became `due`.

    Runs once per load, right after the file is read, so everything
    downstream - raw-dict reads like get_item_attr included - only ever sees
    the current names; the next commit writes them back out under the new
    ones. A legacy `due_by` only fills in `due` when it has a value and `due`
    doesn't, and the legacy key is dropped either way so it can't linger.
    """
    for item in user_data.todo_items.values():
        if "due_by" in item:
            legacy_due = item.pop("due_by")
            if legacy_due and not item.get("due"):
                item["due"] = legacy_due

    # a saved DISPLAY_STRING can name the old attribute too (the default
    # used to, and `task config set` persists every default it fills in)
    display_string = user_data.config.get("DISPLAY_STRING")
    if display_string:
        user_data.config["DISPLAY_STRING"] = " ".join(
            "due" if attr == "due_by" else attr for attr in display_string.split(" ")
        )


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
                    _migrate_legacy_keys(self.user_data)
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
        # leave the db in the same valid, connected, empty state a
        # first-ever run would - otherwise the in-memory user_data is
        # stale and the next commit() fails (no directory to write into)
        self._setup_directory()
        self.user_data = UserData(name=self.user_name)
        self.commit()

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

            if _is_chain_head(self.get_item(child_id)):
                self.delete_chain(child_id)
            else:
                self.delete_item(child_id)


        # remove child from parent
        if item.parent_id is not None:
            self.remove_child_from_parent(item.id, item.parent_id)

        # remove from a parent
        self.remove_node_from_chain(id)

        self._debug(f"Deleting item {id}")
        item_dict = self.user_data.todo_items.pop(str(id))

    def remove_child_from_parent(self, child_id: int, parent_id: int):
        parent = self.get_item(parent_id)
        if child_id not in parent.child_ids:
            raise DatabaseError(f"Cannot delete child {child_id} from parent {parent_id}")
        parent.child_ids.remove(child_id)
        self.update_item(parent_id, child_ids=parent.child_ids)

    def delete_chain(self, node_id: int):
        item = self.get_item(node_id)

        if item.next_chain_id is not None:
            self.delete_chain(item.next_chain_id)
        self.delete_item(node_id)

    def insert_node_into_chain(self, node_id: int, prev_id: int):
        node = self.get_item(node_id)

        # already part of some chain - detach cleanly first rather than
        # overwriting its pointers in place, which would corrupt both
        # chains (its old neighbors would still point at it)
        if node.prev_chain_id is not None or node.next_chain_id is not None:
            self.remove_node_from_chain(node_id)
            node = self.get_item(node_id)

        # a chain member is tree-invisible except through its head - pop it
        # off its current parent (if any) instead of leaving it doubly
        # reachable, as both a tree child and a chain link
        if node.parent_id is not None:
            self.remove_child_from_parent(node.id, node.parent_id)
            self.update_item(node.id, parent_id=None)
            node = self.get_item(node_id)

        prev = self.get_item(prev_id)

        # prev already had a next -> insert and update refs
        if prev.next_chain_id is not None:
            node.next_chain_id = prev.next_chain_id
            self.update_item(node.next_chain_id, prev_chain_id=node_id)

        # update prev to point to node
        node.prev_chain_id = prev_id
        prev.next_chain_id = node_id

        self.update_item(**prev.model_dump())
        self.update_item(**node.model_dump())

    def remove_node_from_chain(self, node_id: int):
        node = self.get_item(node_id)

        if node.prev_chain_id is not None and node.next_chain_id is not None:
            
            self.update_item(node.prev_chain_id, next_chain_id=node.next_chain_id)
            self.update_item(node.next_chain_id, prev_chain_id =node.prev_chain_id)

        elif node.prev_chain_id is not None:
            self.update_item(node.prev_chain_id, next_chain_id=None)

        elif node.next_chain_id is not None:
            next_id = node.next_chain_id
            self.update_item(next_id, prev_chain_id=None)

            # node was the chain's tree entry point (the head) - the chain's
            # entry point just moved to `next_id`, so it needs node's old
            # parent slot too, not just the `parent_id` field on its own
            # (which alone would leave the parent's child_ids still
            # pointing at node, orphaning the rest of the chain)
            if node.parent_id is not None:
                self.update_item(next_id, parent_id=node.parent_id)
                self.add_child_to_parent(next_id, node.parent_id)

        node.next_chain_id = None
        node.prev_chain_id = None
        self.update_item(**node.model_dump())

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

    def remove_config_value(self, key: str) -> bool:
        # drop the key entirely rather than setting it to None - most
        # CLIConfig fields aren't Optional, so writing None through
        # update_config()/CLIConfig(**dict) would fail validation.
        # Removing the key just falls back to that field's own default.
        self.user_data.config.pop(key, None)

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
