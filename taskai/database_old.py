import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional, Literal, Any
from dataclasses import dataclass
import psycopg2
import psycopg2.extras
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Database:
    type: Literal["sqlite","postgres"]
    connection: Any  # the database connection
    url: str = None
    
    @property
    def placeholder(self) -> str:
        return "?" if self.type == "sqlite" else "%s"


def get_db() -> Database:
    database_url  = os.getenv("DATABASE_URL")
    if database_url:

        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://",1)
        conn = psycopg2.connect(database_url, cursor_factory=psycopg2.extras.RealDictCursor)
        db_type = "postgres"
    else:
        raise RuntimeError("DATABASE_URL environment variable not defined")

    database = Database(
        type=db_type,
        connection=conn,
        url=database_url
    )
    return database

def init_database():

    """Create the database and tables if they don't exist"""
    db = get_db()
    conn = db.connection
    cursor = conn.cursor()

    ID_TYPE = "INTEGER PRIMARY KEY AUTOINCREMENT" if db.type == "sqlite" else "SERIAL PRIMARY KEY"

    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS todos (
            id {ID_TYPE},
            text TEXT NOT NULL,
            person_name TEXT NOT NULL,
            completed BOOLEAN DEFAULT FALSE,
            due_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()


def add_todo(text: str, person_name: str, due_date: Optional[str] = None, user_id: Optional[1] = None) -> int:
    """Add a new todo to the database"""
    logger.info("Adding To-do")
    logger.debug(f"""
    text:        {text}
    person_name: {person_name}
    due_date:    {due_date or ""}
    user_id:     {user_id or ""}
    """)
    db = get_db()
    conn = db.connection
    ph = db.placeholder
    cursor = conn.cursor()
    cursor.execute(f'''
        INSERT INTO todos (text, person_name, due_date)
        VALUES ({ph}, {ph}, {ph})
    ''', (text, person_name, due_date))

    todo_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # print(f"Added todo: {text} by {person_name}")
    return todo_id

def get_todo(id_) -> dict:
    logger.info("Getting Todo")
    logger.debug(f"""
    id: {id_}
    """)
    db = get_db()
    conn = db.connection
    cursor = conn.cursor()
    cursor.execute(f'''
        SELECT id, text, person_name, completed, due_date, created_at
        FROM todos
        WHERE id = {db.placeholder}
    ''', (id_,))

    rows = cursor.fetchall()
    conn.close()

    if db.type == "sqlite":
        todos = [
            {
                "id": row[0],
                "text": row[1],
                "person_name": row[2],
                "completed": row[3],
                "due_date": row[4],
                "created_at": row[5],
            } for row in rows
        ]
    else:
        todos = [
            {
                "id": row["id"],
                "text": row["text"],
                "person_name": row["person_name"],
                "completed": row["completed"],
                "due_date": row["due_date"],
                "created_at": row["created_at"],
            } for row in rows
        ]


    return todos[0]


def get_all_todos() -> list[dict]:
    logger.info("Getting All Todos")

    db = get_db()
    conn = db.connection
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, text, person_name, completed, due_date, created_at
        FROM todos
        ORDER BY created_at DESC
    ''')

    rows = cursor.fetchall()
    conn.close()

    if db.type == "sqlite":
        todos = [
            {
                "id": row[0],
                "text": row[1],
                "person_name": row[2],
                "completed": row[3],
                "due_date": row[4],
                "created_at": row[5],
            } for row in rows
        ]
    else:
        todos = [
            {
                "id": row["id"],
                "text": row["text"],
                "person_name": row["person_name"],
                "completed": row["completed"],
                "due_date": row["due_date"],
                "created_at": row["created_at"],
            } for row in rows
        ]


    return todos


def toggle_todo_complete(todo_id: int) -> bool:
    """Toggle the completion status of a todo"""
    logger.info("Setting Todo to complete")
    logger.debug(f"""
    todo_id: {todo_id}
    """)
    db = get_db()
    conn = db.connection
    cursor = conn.cursor()
    ph = db.placeholder
    cursor.execute(f'SELECT completed FROM todos WHERE id = {ph}', (todo_id,))
    
    result = cursor.fetchone()

    if not result:
        conn.close()
        return False

    new_status = not bool(result[0] if db.type == "sqlite" else result["completed"])
    cursor.execute(f'UPDATE todos SET completed = {ph} WHERE id = {ph}', (new_status, todo_id))

    conn.commit()
    conn.close()
    return True


def update_todo(id: int, text: str, person_name: str, due_date: Optional[str] = None) -> int:
    """Add a new todo to the database"""
    logger.info("Adding To-do")
    logger.debug(f"""
    text:        {text}
    person_name: {person_name}
    due_date:    {due_date or ""}
    """)
    db = get_db()
    conn = db.connection
    ph = db.placeholder
    cursor = conn.cursor()
    
    try:
        cursor.execute(f'''
            UPDATE todos
            SET text = {db.placeholder}, person_name = {db.placeholder}, due_date = {db.placeholder}
            WHERE id = {db.placeholder};
        ''', (text, person_name, due_date, id))

        conn.commit()
        conn.close()

        # print(f"Updated todo: {text} by {person_name}")
        return True
    except Exception as e:
        # print(e)
        return False


def delete_todo(todo_id: int) -> bool:
    """Delete a todo by ID"""
    logger.info("Deleting Todo")
    logger.debug(f"""
    todo_id: {todo_id}
    """)
    db = get_db()
    conn = db.connection
    cursor = conn.cursor()
    ph = db.placeholder
    cursor.execute(f'DELETE FROM todos WHERE id = {ph}', (todo_id,))
    deleted_rows = cursor.rowcount

    conn.commit()
    conn.close()

    return deleted_rows > 0


# --- Users ---

def get_user_by_id(user_id: int) -> dict | None:

    logger.info("Getting user by ID")
    logger.debug(f"""
    user_id: {user_id}
    """)

    db = get_db()
    conn = db.connection
    cur = conn.cursor()
    cur.execute(f"SELECT id, username, email, telegram_chat_id FROM users WHERE id = {db.placeholder}", (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    if db.type == "sqlite":
        return {"id": row[0], "username": row[1], "email": row[2], "telegram_chat_id": row[3]}
    return dict(row)

def get_user_by_username_or_email(value: str) -> dict | None:
    logger.info("Getting user by username or email")
    logger.debug(f"""
    value: {value}
    """)
    db = get_db()
    conn = db.connection
    cur = conn.cursor()
    ph = db.placeholder
    cur.execute(
        f"SELECT id, username, email, password_hash FROM users WHERE username = {ph} OR email = {ph}",
        (value, value)
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    if db.type == "sqlite":
        return {"id": row[0], "username": row[1], "email": row[2], "password_hash": row[3]}
    return dict(row)

def create_user(username: str, email: str | None, password_hash: str | None) -> int:
    logger.info("Creating User")
    logger.debug(f"""
    username:      {username}
    email:         {email}
    password_hash: {password_hash}
    """)
    db = get_db()
    conn = db.connection
    ph = db.placeholder
    cur = conn.cursor()
    cur.execute(
        f"INSERT INTO users (username, email, password_hash) VALUES ({ph}, {ph}, {ph})",
        (username, email, password_hash)
    )
    user_id = cur.lastrowid
    conn.commit()
    conn.close()
    return user_id

# --- Lists ---

def create_list(name: str, owner_id: int) -> int:
    logger.info("Creating List")
    logger.debug(f"""
    name:      {name}
    owner_id:  {owner_id}
    """)
    db = get_db()
    conn = db.connection
    ph = db.placeholder
    cur = conn.cursor()
    cur.execute(f"INSERT INTO lists (name, owner_id) VALUES ({ph}, {ph})", (name, owner_id))
    list_id = cur.lastrowid
    cur.execute(
        f"INSERT INTO list_members (list_id, user_id, status) VALUES ({ph}, {ph}, 'active')",
        (list_id, owner_id)
    )
    conn.commit()
    conn.close()
    return list_id

if __name__ == "__main__":
    init_database()

