# local
from taskai.json_dir_database import JsonDirectoryDatabase
from taskai.models import TodoItem, TodoList

# external
from rich import print

def repair_database_service(
        db: JsonDirectoryDatabase
):
    
    """
    Repairs the json database
    """
    print(("Pruning null item references in lists ..."))
    for list_id in db.lists:
        list_: TodoList = db.read(list_id)

        new_list_item_ids = []
        for item_id in list_.item_ids:
            if item_id not in db.items:
                print(f"Pruned reference to null item id {item_id}")
            else:
                new_list_item_ids.append(item_id)
        list_.item_ids = new_list_item_ids
        db.update(list_)
    
    print("Pruning orphan items")
    bad_item_ids = set()
    for item_id in db.items:
        item: TodoItem = db.read(item_id)
        if item.list_id not in db.lists:
            print(f"Pruning orphan item {item_id}")
            db.delete(bad_item_ids)
            

    db.commit()
    print("Repair complete!")

