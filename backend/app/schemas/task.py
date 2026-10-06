
from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, ConfigDict


TaskStatus = Literal[
    "backlog", "todo", "in_progress", "blocked", "review", "done", "cancelled"
]
TaskPriority = Literal["low", "medium", "high", "urgent"]


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    status: TaskStatus = "backlog"
    priority: TaskPriority = "medium"
    assignee_id: Optional[int] = None
    due_date: Optional[date] = None
    estimated_hours: Optional[Decimal] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    assignee_id: Optional[int] = None
    due_date: Optional[date] = None
    estimated_hours: Optional[Decimal] = None
    actual_hours: Optional[Decimal] = None


class TaskStatusChange(BaseModel):
    status: TaskStatus


class TaskAssign(BaseModel):
    assignee_id: int


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: Optional[str]
    project_id: int
    assignee_id: Optional[int]
    reporter_id: int
    status: str
    priority: str
    due_date: Optional[date]
    estimated_hours: Optional[Decimal]
    actual_hours: Optional[Decimal]
    position: int
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total: int
    page: int = 1
    page_size: int = 20
    