from fastapi import FastAPI, HTTPException, Depends, Response, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
import taskai.auth as auth
import taskai.database as database
from telegram_dm import send_dm as send_dm_telegram
from loguru import logger
import loguru
from dotenv import load_dotenv
load_dotenv()
import os


logger.level("INFO")

def send_dm(message, person):
    print("SEND_TEXT_UPDATES:", os.getenv("SEND_TEXT_UPDATES"))
    if os.getenv("SEND_TEXT_UPDATES"):
        send_dm_telegram(message, person)
    else:
        print(f"To {person}: {message}")

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"))


class TodoCreate(BaseModel):
    text: str
    person_name: str
    due_date: Optional[str] = None

class TodoUpdate(BaseModel):
    id: int
    text: str
    person_name: str
    due_date: Optional[str] = None


class TodoResponse(BaseModel):
    id: int
    text: str
    person_name: str
    completed: bool
    due_date: Optional[str]
    created_at: str

class RegisterRequest(BaseModel):
    username: str
    email: Optional[str] = None
    password: str

class LoginRequest(BaseModel):
    username_or_email: str
    password: str


@app.get("/api/todos")
def get_todos(user=Depends(auth.get_current_user)):
    """Get all todos"""
    todos = database.get_all_todos()
    return {"todos": todos}


@app.post("/api/todos")
def create_todo(todo: TodoCreate, user_id=Depends(auth.get_current_user)):
    """Create a new todo"""
    todo_id = database.add_todo(todo.text, todo.person_name, todo.due_date)
    for person in ("maddie","alex"):
        send_dm(f"""
    Todo created: 
    Description: {todo.text}
    Person: {todo.person_name}
    Due Date: {todo.due_date}
        """, person)

    return {"id": todo_id, "message": "Todo created successfully"}


@app.put("/api/todos/{todo_id}/complete")
def toggle_todo_complete(todo_id: int, user_id=Depends(auth.get_current_user)):
    """Toggle todo completion status"""
    success = database.toggle_todo_complete(todo_id)

    if success:
        todo = database.get_todo(todo_id)

        for person in ("maddie","alex"):
            if todo['completed']:
                send_dm(f"'{todo['text']}' has been crossed off!", person)
            else:
                send_dm(f"'{todo['text']}' has been marked as not done", person)

    if not success:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"message": "Todo updated successfully"}


@app.delete("/api/todos/{todo_id}")
def delete_todo(todo_id: int, user_id=Depends(auth.get_current_user)):
    """Delete a todo"""

    success = database.delete_todo(todo_id)
    if not success:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"message": "Todo deleted successfully"}


@app.put("/api/todos")
def update_todo(
    todo: TodoUpdate,
    user_id=Depends(auth.get_current_user)
):
    success = database.update_todo(
        id=todo.id,
        text=todo.text,
        person_name=todo.person_name,
        due_date=todo.due_date if todo.due_date else None
    )

    if not success:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"message": "Todo updated successfully"}



@app.get("/")
def read_root():
    return FileResponse(path="static/index.html")


@app.post("/auth/register")
def register(req: RegisterRequest, response: Response):
    
    if database.get_user_by_username_or_email(req.username):
        raise HTTPException(status_code=400, detail="Username already taken")
    
    pw_hash = auth.hash_password(req.password)
    user_id = database.create_user(req.username, req.email, pw_hash)
    database.create_list("Personal", user_id)
    token = auth.create_token(user_id)
    response.set_cookie(auth.COOKIE_NAME, token, httponly=True,
                        samesite="lax", max_age=86400*30)
    return {"message": "Registered successfully"}

@app.post("/auth/login")
def login(req: LoginRequest, response: Response):

    logger.debug(f"username_or_email: req.{req.username_or_email}")
    logger.debug(f"password: {req.password}")

    user = database.get_user_by_username_or_email(req.username_or_email)
    if not user or not auth.verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = auth.create_token(user["id"])
    response.set_cookie(auth.COOKIE_NAME, token, httponly=True,
                        samesite="lax", max_age=86400*30)
    return {"message": "Logged in"}

@app.post("/auth/logout")
def logout(response:Response):
    response.delete_cookie(auth.COOKIE_NAME)
    return {"message": "Logged out"}

@app.get("/api/users/me")
def me(user_id=Depends(auth.get_current_user)):
    return user_id

if os.getenv("RUN_MODE") == "dev":
    print("running in dev mode")
    print("logging out")
    print(me())
