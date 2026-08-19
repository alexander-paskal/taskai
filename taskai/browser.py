from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


app = FastAPI()

app.mount("/static", StaticFiles(directory="taskai/static"), name="static")

@app.get("/", response_class=FileResponse)
def index():
    return FileResponse("taskai/static/index.html")