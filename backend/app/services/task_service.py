
from datetime import date
from decimal import Decimal

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.models.task import Task, TaskDependency
from app.models.project import Project
from app.models.organization_member import OrganizationMember
from app.models.user import User
from app.models.role import Role
from app.schemas.task import TaskCreate, TaskUpdate


# Valid status transitions
VALID_TRANSITIONS = {
    "backlog": {"todo", "cancelled"},
    "todo": {"in_progress", "cancelled", "backlog"},
    "in_progress": {"blocked", "review", "cancelled"},
    "blocked": {"in_progress", "cancelled"},
    "review": {"done", "in_progress", "cancelled"},
    "done": set(),          # terminal
    "cancelled": set(),     # terminal
}


class TaskServiceError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def _get_project_or_404(db: Session, project_id: int, organization_id: int) -> Project:
    project = db.scalar(
        select(Project).where(
            Project.id == project_id,
            Project.organization_id == organization_id,
        )
    )
    if not project:
        raise TaskServiceError("PROJECT_NOT_FOUND", "Project not found in this organization.")
    return project


def _user_belongs_to_org(db: Session, user_id: int, organization_id: int) -> bool:
    membership = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.user_id == user_id,
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.is_active == True,  # noqa
        )
    )
    return membership is not None


def _get_user_role(db: Session, user_id: int, organization_id: int) -> str | None:
    row = db.execute(
        select(Role.name)
        .join(OrganizationMember, OrganizationMember.role_id == Role.id)
        .where(
            OrganizationMember.user_id == user_id,
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.is_active == True,  # noqa
        )
    ).scalar_one_or_none()
    return row


def create_task(
    db: Session,
    *,
    project_id: int,
    organization_id: int,
    reporter_id: int,
    data: TaskCreate,
) -> Task:
    _get_project_or_404(db, project_id, organization_id)

    if data.assignee_id is not None:
        _validate_assignee(db, data.assignee_id, organization_id)

    task = Task(
        title=data.title.strip(),
        description=data.description,
        project_id=project_id,
        assignee_id=data.assignee_id,
        reporter_id=reporter_id,
        status=data.status,
        priority=data.priority,
        due_date=data.due_date,
        estimated_hours=data.estimated_hours,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def list_tasks(
    db: Session,
    *,
    project_id: int,
    organization_id: int,
    status: str | None = None,
    priority: str | None = None,
    assignee_id: int | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Task], int]:
    _get_project_or_404(db, project_id, organization_id)

    query = select(Task).where(Task.project_id == project_id)

    if status:
        query = query.where(Task.status == status)
    if priority:
        query = query.where(Task.priority == priority)
    if assignee_id:
        query = query.where(Task.assignee_id == assignee_id)
    if search:
        query = query.where(Task.title.ilike(f"%{search}%"))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0

    items = db.scalars(
        query.order_by(Task.position, Task.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return list(items), total


def get_task(
    db: Session,
    *,
    task_id: int,
    project_id: int,
    organization_id: int,
) -> Task:
    _get_project_or_404(db, project_id, organization_id)

    task = db.scalar(
        select(Task).where(Task.id == task_id, Task.project_id == project_id)
    )
    if not task:
        raise TaskServiceError("TASK_NOT_FOUND", "Task not found.")
    return task


def update_task(
    db: Session,
    *,
    task_id: int,
    project_id: int,
    organization_id: int,
    data: TaskUpdate,
) -> Task:
    task = get_task(db, task_id=task_id, project_id=project_id, organization_id=organization_id)

    if data.status is not None and data.status != task.status:
        _validate_transition(task.status, data.status)
        _check_dependencies_completed(db, task)

    if data.assignee_id is not None:
        _validate_assignee(db, data.assignee_id, organization_id)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return task


def change_status(
    db: Session,
    *,
    task_id: int,
    project_id: int,
    organization_id: int,
    new_status: str,
) -> Task:
    task = get_task(db, task_id=task_id, project_id=project_id, organization_id=organization_id)
    _validate_transition(task.status, new_status)
    _check_dependencies_completed(db, task)

    task.status = new_status
    db.commit()
    db.refresh(task)
    return task


def assign_task(
    db: Session,
    *,
    task_id: int,
    project_id: int,
    organization_id: int,
    assignee_id: int,
) -> Task:
    task = get_task(db, task_id=task_id, project_id=project_id, organization_id=organization_id)
    _validate_assignee(db, assignee_id, organization_id)

    task.assignee_id = assignee_id
    db.commit()
    db.refresh(task)
    return task


def delete_task(
    db: Session,
    *,
    task_id: int,
    project_id: int,
    organization_id: int,
) -> None:
    task = get_task(db, task_id=task_id, project_id=project_id, organization_id=organization_id)
    db.delete(task)
    db.commit()


def add_dependency(
    db: Session,
    *,
    task_id: int,
    depends_on_task_id: int,
    project_id: int,
    organization_id: int,
) -> TaskDependency:
    if task_id == depends_on_task_id:
        raise TaskServiceError("INVALID_DEPENDENCY", "A task cannot depend on itself.")

    task = get_task(db, task_id=task_id, project_id=project_id, organization_id=organization_id)
    depends_on = get_task(
        db, task_id=depends_on_task_id, project_id=project_id, organization_id=organization_id
    )

    # Prevent circular dependencies (simple check)
    if _would_create_cycle(db, task_id, depends_on_task_id):
        raise TaskServiceError("CIRCULAR_DEPENDENCY", "This dependency would create a cycle.")

    existing = db.scalar(
        select(TaskDependency).where(
            TaskDependency.task_id == task_id,
            TaskDependency.depends_on_task_id == depends_on_task_id,
        )
    )
    if existing:
        raise TaskServiceError("DEPENDENCY_EXISTS", "Dependency already exists.")

    dep = TaskDependency(task_id=task_id, depends_on_task_id=depends_on_task_id)
    db.add(dep)
    db.commit()
    db.refresh(dep)
    return dep


# ---------- helpers ----------

def _validate_transition(current: str, new: str) -> None:
    allowed = VALID_TRANSITIONS.get(current, set())
    if new not in allowed:
        raise TaskServiceError(
            "INVALID_STATUS_TRANSITION",
            f"Cannot move from '{current}' to '{new}'. Allowed: {sorted(allowed) or 'none'}.",
        )


def _validate_assignee(db: Session, assignee_id: int, organization_id: int) -> None:
    user = db.get(User, assignee_id)
    if not user or not user.is_active:
        raise TaskServiceError("INVALID_ASSIGNEE", "Assignee not found or inactive.")

    if not _user_belongs_to_org(db, assignee_id, organization_id):
        raise TaskServiceError("ASSIGNEE_NOT_IN_ORG", "Assignee does not belong to this organization.")

    role = _get_user_role(db, assignee_id, organization_id)
    if role == "Viewer":
        raise TaskServiceError("VIEWER_CANNOT_BE_ASSIGNED", "Viewers cannot be assigned tasks.")


def _check_dependencies_completed(db: Session, task: Task) -> None:
    """Block moving forward if any dependency is not done."""
    deps = db.scalars(
        select(TaskDependency).where(TaskDependency.task_id == task.id)
    ).all()
    for dep in deps:
        parent = db.get(Task, dep.depends_on_task_id)
        if parent and parent.status != "done":
            raise TaskServiceError(
                "DEPENDENCY_NOT_COMPLETED",
                f"Task depends on '{parent.title}' which is not completed yet.",
            )


def _would_create_cycle(db: Session, task_id: int, depends_on_id: int) -> bool:
    """Simple BFS to detect if adding edge depends_on_id → task_id creates a cycle."""
    visited = set()
    stack = [task_id]
    while stack:
        current = stack.pop()
        if current == depends_on_id:
            return True
        if current in visited:
            continue
        visited.add(current)
        children = db.scalars(
            select(TaskDependency.task_id).where(
                TaskDependency.depends_on_task_id == current
            )
        ).all()
        stack.extend(children)
    return False

