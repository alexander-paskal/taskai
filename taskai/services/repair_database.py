# local
from taskai.json_dir_database import JsonDirectoryDatabase
from taskai.models import TodoItem

# external
from rich import print

def repair_database_service(
        db: JsonDirectoryDatabase
):
    """
    Reconciles parent/child links and prunes dangling id references.

    Parent/child/link id-lists are maintained by hand on both sides of
    every relationship (see json_dir_database.py) - it's easy for a future
    change to desync them by touching one side and not the other, or to
    leave a dangling reference behind after a delete. This walks every
    item and fixes both classes of issue.
    """
    print("Checking item tree consistency")
    fixed = 0
    all_ids = set(db.get_item_ids())

    for item_id in db.get_item_ids():
        item = db.get_item(item_id)

        # parent_id must point to a real item, and this item must be
        # listed in that parent's child_ids
        if item.parent_id is not None:
            if item.parent_id not in all_ids:
                db.update_item(item.id, parent_id=None)
                fixed += 1
            else:
                parent = db.get_item(item.parent_id)
                if item.id not in parent.child_ids:
                    db.update_item(parent.id, child_ids=parent.child_ids + [item.id])
                    fixed += 1

        # child_ids and linked_ids can both be left dangling after a
        # delete - drop any id that no longer exists
        for field in ("child_ids", "linked_ids"):
            ids = getattr(item, field)
            valid_ids = [id_ for id_ in ids if id_ in all_ids]
            if valid_ids != ids:
                db.update_item(item.id, **{field: valid_ids})
                fixed += 1

    db.commit()
    print(f"Repair complete! Fixed {fixed} issue(s).")

