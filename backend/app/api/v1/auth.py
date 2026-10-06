
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.models.user import User

from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import login_user, refresh_access_token, register_user, logout_user
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
    
#===============================================================

@router.get(
    "/me",
    response_model=UserResponse,
)
def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user
    
    
#===============================================================

@router.post(
    "/refresh",
    response_model=TokenResponse,
)
def refresh_token(
    data: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    try:
        access_token, new_refresh_token = refresh_access_token(
            db=db,
            refresh_token=data.refresh_token,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_REFRESH_TOKEN",
                "message": str(exc),
            },
        )

    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "REFRESH_NOT_ALLOWED",
                "message": str(exc),
            },
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "REFRESH_CONFIGURATION_ERROR",
                "message": str(exc),
            },
        )

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    

@router.post("/logout")
def logout(
    data: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    try:
        logout_user(
            db=db,
            refresh_token=data.refresh_token,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_REFRESH_TOKEN",
                "message": str(exc),
            },
        )

    return {
        "message": "Logout successful."
    }
    
    
    

# ============================================================
# GitHub OAuth
# ============================================================

from fastapi import Query
from fastapi.responses import RedirectResponse
from app.services.auth_service import exchange_github_code, login_or_register_github_user
from urllib.parse import urlencode
import secrets


@router.get("/github/login")
def github_login():
    """Redirect user to GitHub authorization page."""
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "GITHUB_OAUTH_NOT_CONFIGURED",
                "message": "GitHub OAuth client ID is not configured.",
            },
        )

    # CSRF state
    state = secrets.token_urlsafe(32)

    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": settings.GITHUB_REDIRECT_URI,
        "scope": "read:user user:email",
        "state": state,
    }
    url = f"https://github.com/login/oauth/authorize?{urlencode(params)}"
    return RedirectResponse(url)


@router.get("/github/callback")
async def github_callback(
    code: str = Query(...),
    state: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """Handle GitHub OAuth callback, create/login user, redirect to frontend with tokens."""
    try:
        github_data = await exchange_github_code(code)
        user, organization, role, access_token, refresh_token = login_or_register_github_user(
            db=db,
            github_data=github_data,
        )
    except ValueError as exc:
        # Redirect to frontend with error
        error_params = urlencode({"error": str(exc)})
        return RedirectResponse(
            f"{settings.FRONTEND_URL}/login?{error_params}"
        )
    except PermissionError as exc:
        error_params = urlencode({"error": str(exc)})
        return RedirectResponse(
            f"{settings.FRONTEND_URL}/login?{error_params}"
        )

    # Success – redirect to frontend with tokens in query (frontend should store them)
    # In production prefer a short-lived one-time code or httpOnly cookie.
    success_params = urlencode({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": str(settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60),
    })
    return RedirectResponse(
        f"{settings.FRONTEND_URL}/auth/callback?{success_params}"
    )
