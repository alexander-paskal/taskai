from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from taskai.cli import db


app = FastAPI()

app.mount("/static", StaticFiles(directory="taskai/static"), name="static")

@app.get("/", response_class=FileResponse)
def index():
    return FileResponse("taskai/static/index.html")

@app.get("/api/tree")
def get_tree():
    return {
        item_id: db.get_item(item_id).model_dump(mode="json")
        for item_id in db.get_item_ids()
    }