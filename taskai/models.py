# standard lib
from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timedelta

# external
from pydantic import Field, BaseModel

class Base(BaseModel):
    pass

    @classmethod
    def from_model(cls, model: "Base", **kwargs) -> "Base":
        model_kwargs = model.model_dump()
        model_kwargs.update(kwargs)
        return cls(model_kwargs)


class UserData(Base):
    # serialized versions of the data
    todo_items: dict[str, dict] = Field(default_factory=dict)
    comments: dict[str, dict] = Field(default_factory=dict)
    config: dict = Field(default_factory=dict)

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    id_counter: int = 0
    # password stuff

class TodoItem(Base):
    name: str = Field(index=True)

    id: Optional[int] = Field(default=None, primary_key=True)
    parent_id: Optional[int] = None
    user_id: Optional[str] = None
    created_on: datetime = Field(default_factory=datetime.now)
    completed: bool = False
    description: str = ""
    due_by: Optional[datetime] = None
    comment_ids: list[int] = Field(default_factory=list)
    dependency_ids: list[int] = Field(default_factory=list)
    child_ids: list[int] = Field(default_factory=list)
    priority: int = 0
    recurs_every: Optional[list[timedelta]] = None
    recurs_until: Optional[datetime] = None 
    recur_keep_incomplete: bool = False


class Comment(Base):
    content: str

    item_id: Optional[int] = None
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[str] = None
    created_on: datetime = Field(default_factory=datetime.now)

class CLIConfig(Base):

    # GEMINI
    GEMINI_MODEL: str = None
    GEMINI_API_KEY: str = None

class LLMConfig(Base):
    pass
