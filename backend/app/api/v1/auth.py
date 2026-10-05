
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import login_user, register_user
from app.core.config import settings



router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db),
):
    try:
        user, organization, role = register_user(
            db=db,
            data=data,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "REGISTRATION_CONFLICT",
                "message": str(exc),
            },
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "REGISTRATION_CONFIGURATION_ERROR",
                "message": str(exc),
            },
        )

    return RegisterResponse(
        message="Registration successful.",
        user=UserResponse.model_validate(user),
        organization_id=organization.id,
        role=role.name,
    )
    
#===============================================================

@router.post(
    "/login",
    response_model=LoginResponse,
)
def login(
    data: LoginRequest,
    db: Session = Depends(get_db),
):
    try:
        (
            user,
            membership,
            role,
            access_token,
            refresh_token,
        ) = login_user(
            db=db,
            email=data.email,
            password=data.password,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_CREDENTIALS",
                "message": str(exc),
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "LOGIN_NOT_ALLOWED",
                "message": str(exc),
            },
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "LOGIN_CONFIGURATION_ERROR",
                "message": str(exc),
            },
        )

    return LoginResponse(
        message="Login successful.",
        user=UserResponse.model_validate(user),
        organization_id=membership.organization_id,
        role=role.name,
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        ),
    )
    
    
    