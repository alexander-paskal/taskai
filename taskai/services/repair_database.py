# local
from taskai.json_dir_database import JsonDirectoryDatabase
from taskai.models import TodoItem

# external
from rich import print

def repair_database_service(
        db: JsonDirectoryDatabase
):
    
    """
    Repairs the json database
    """        
    print("Fixing Item Levels")
    fixed = False
    while not fixed:
        fixed = True

        for k, item in db.items.items():
            
            if item["parent_id"]:
                parent_level = db.items[item["parent_id"]]["level"]
                if item["level"] != parent_level + 1:
                    item["level"] += 1
                    fixed = False
    
    for k, item in db.items.items():
        assert item["level"] == db.items[item["parent_id"]]["level"] + 1
    
    db.commit()
    print("Repair complete!")

