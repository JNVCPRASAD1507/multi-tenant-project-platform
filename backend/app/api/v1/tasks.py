
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskListResponse,
    TaskStatusChange,
    TaskAssign,
)
from app.services.task_service import (
    TaskServiceError,
    create_task,
    list_tasks,
    get_task,
    update_task,
    change_status,
    assign_task,
    delete_task,
    add_dependency,
)

router = APIRouter(tags=["Tasks"])


def _handle_error(exc: TaskServiceError):
    code_map = {
        "PROJECT_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "TASK_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "INVALID_STATUS_TRANSITION": status.HTTP_409_CONFLICT,
        "DEPENDENCY_NOT_COMPLETED": status.HTTP_409_CONFLICT,
        "CIRCULAR_DEPENDENCY": status.HTTP_409_CONFLICT,
        "INVALID_ASSIGNEE": status.HTTP_400_BAD_REQUEST,
        "ASSIGNEE_NOT_IN_ORG": status.HTTP_400_BAD_REQUEST,
        "VIEWER_CANNOT_BE_ASSIGNED": status.HTTP_400_BAD_REQUEST,
        "INVALID_DEPENDENCY": status.HTTP_400_BAD_REQUEST,
        "DEPENDENCY_EXISTS": status.HTTP_409_CONFLICT,
    }
    raise HTTPException(
        status_code=code_map.get(exc.code, status.HTTP_400_BAD_REQUEST),
        detail={"code": exc.code, "message": exc.message},
    )


@router.post(
    "/organizations/{organization_id}/projects/{project_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_task_endpoint(
    organization_id: int,
    project_id: int,
    data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # TODO: add proper permission check using has_permission
    try:
        task = create_task(
            db,
            project_id=project_id,
            organization_id=organization_id,
            reporter_id=current_user.id,
            data=data,
        )
        return task
    except TaskServiceError as e:
        _handle_error(e)


@router.get(
    "/organizations/{organization_id}/projects/{project_id}/tasks",
    response_model=TaskListResponse,
)
def list_tasks_endpoint(
    organization_id: int,
    project_id: int,
    status: str | None = None,
    priority: str | None = None,
    assignee_id: int | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        items, total = list_tasks(
            db,
            project_id=project_id,
            organization_id=organization_id,
            status=status,
            priority=priority,
            assignee_id=assignee_id,
            search=search,
            page=page,
            page_size=page_size,
        )
        return TaskListResponse(items=items, total=total, page=page, page_size=page_size)
    except TaskServiceError as e:
        _handle_error(e)


@router.get(
    "/organizations/{organization_id}/projects/{project_id}/tasks/{task_id}",
    response_model=TaskResponse,
)
def get_task_endpoint(
    organization_id: int,
    project_id: int,
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return get_task(
            db, task_id=task_id, project_id=project_id, organization_id=organization_id
        )
    except TaskServiceError as e:
        _handle_error(e)


@router.patch(
    "/organizations/{organization_id}/projects/{project_id}/tasks/{task_id}",
    response_model=TaskResponse,
)
def update_task_endpoint(
    organization_id: int,
    project_id: int,
    task_id: int,
    data: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return update_task(
            db,
            task_id=task_id,
            project_id=project_id,
            organization_id=organization_id,
            data=data,
        )
    except TaskServiceError as e:
        _handle_error(e)


@router.post(
    "/organizations/{organization_id}/projects/{project_id}/tasks/{task_id}/status",
    response_model=TaskResponse,
)
def change_status_endpoint(
    organization_id: int,
    project_id: int,
    task_id: int,
    data: TaskStatusChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return change_status(
            db,
            task_id=task_id,
            project_id=project_id,
            organization_id=organization_id,
            new_status=data.status,
        )
    except TaskServiceError as e:
        _handle_error(e)


@router.post(
    "/organizations/{organization_id}/projects/{project_id}/tasks/{task_id}/assign",
    response_model=TaskResponse,
)
def assign_task_endpoint(
    organization_id: int,
    project_id: int,
    task_id: int,
    data: TaskAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return assign_task(
            db,
            task_id=task_id,
            project_id=project_id,
            organization_id=organization_id,
            assignee_id=data.assignee_id,
        )
    except TaskServiceError as e:
        _handle_error(e)


@router.delete(
    "/organizations/{organization_id}/projects/{project_id}/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_task_endpoint(
    organization_id: int,
    project_id: int,
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        delete_task(
            db, task_id=task_id, project_id=project_id, organization_id=organization_id
        )
    except TaskServiceError as e:
        _handle_error(e)


@router.post(
    "/organizations/{organization_id}/projects/{project_id}/tasks/{task_id}/dependencies",
    status_code=status.HTTP_201_CREATED,
)
def add_dependency_endpoint(
    organization_id: int,
    project_id: int,
    task_id: int,
    depends_on_task_id: int = Query(..., description="ID of the task this one depends on"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        dep = add_dependency(
            db,
            task_id=task_id,
            depends_on_task_id=depends_on_task_id,
            project_id=project_id,
            organization_id=organization_id,
        )
        return {"id": dep.id, "task_id": dep.task_id, "depends_on_task_id": dep.depends_on_task_id}
    except TaskServiceError as e:
        _handle_error(e)
        

