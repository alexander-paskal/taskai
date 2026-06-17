# standard lib
from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timedelta

# external
from pydantic import Field, BaseModel

class Base(BaseModel):
    pass

@dataclass
class PostgresConfig:
    pass

class User(Base):
    id: Optional[str] = Field(default=None, primary_key=True)
    name: str
    
    id_counter: int = 1
    # password stuff

class TodoList(Base):
    name: str

    id: Optional[str] = Field(default=None, primary_key=True)
    user_id: Optional[str] = None
    item_ids: Optional[list[str]] = Field(default_factory=list)

class TodoItem(Base):
    name: str = Field(index=True)

    id: Optional[str] = Field(default=None, primary_key=True)
    list_id: Optional[str] = None
    user_id: Optional[str] = None
    created_on: datetime = Field(default_factory=datetime.now)
    completed: bool = False
    description: str = ""
    due_by: Optional[datetime] = None
    parent: Optional[str] = None
    comment_ids: list[str] = Field(default_factory=list)
    dependency_ids: list[str] = Field(default_factory=list)
    priority: int = 0
    recurs_every: Optional[list[timedelta]] = None
    recurs_until: Optional[datetime] = None 
    recur_keep_incomplete: bool = False

    def model_post_init(self, context):
        if not self.name:
            self.name = self.name
        return super().model_post_init(context)
    
class Comment(Base):
    content: str

    item_id: Optional[str] = None
    id: Optional[str] = Field(default=None, primary_key=True)
    user_id: Optional[str] = None
    created_on: datetime = Field(default_factory=datetime.now)

class CLIConfig(Base):

    # GEMINI
    GEMINI_MODEL: str = None
    GEMINI_API_KEY: str = None

class LLMConfig(Base):
    pass
