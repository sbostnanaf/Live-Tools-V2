from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from typing import Optional
import structlog

from database.models import User
from database.connection import get_db_session
from api.auth import AuthManager, get_current_user
from utils.validation import validate_password_strength

logger = structlog.get_logger(__name__)
router = APIRouter()
security = HTTPBearer()

# Pydantic models
class UserLogin(BaseModel):
    username: str
    password: str

class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class RefreshToken(BaseModel):
    refresh_token: str

class UserProfile(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    is_admin: bool
    created_at: datetime
    last_login: Optional[datetime] = None

class ChangePassword(BaseModel):
    current_password: str
    new_password: str

@router.post("/register", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """Register a new user"""
    try:
        # Validate password strength
        if not validate_password_strength(user_data.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password does not meet security requirements"
            )
        
        # Check if username already exists
        stmt = select(User).where(User.username == user_data.username)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already registered"
            )
        
        # Check if email already exists
        stmt = select(User).where(User.email == user_data.email)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        
        # Create new user
        from main import app
        auth_manager = app.state.auth_manager
        
        hashed_password = auth_manager.get_password_hash(user_data.password)
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            created_at=datetime.utcnow()
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        # Log registration
        await auth_manager.log_user_action(
            db=db,
            user_id=new_user.id,
            action="user_registered",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            details=f"New user registered: {user_data.username}"
        )
        
        logger.info("User registered successfully", user_id=new_user.id, username=user_data.username)
        
        return UserProfile(
            id=new_user.id,
            username=new_user.username,
            email=new_user.email,
            is_active=new_user.is_active,
            is_admin=new_user.is_admin,
            created_at=new_user.created_at,
            last_login=new_user.last_login
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Registration failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/login", response_model=Token)
async def login(
    user_credentials: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """Authenticate user and return JWT tokens"""
    try:
        from main import app
        auth_manager = app.state.auth_manager
        
        # Authenticate user
        user = await auth_manager.authenticate_user(
            user_credentials.username,
            user_credentials.password,
            db
        )
        
        if not user:
            # Log failed login attempt
            await auth_manager.log_user_action(
                db=db,
                user_id=None,
                action="login_failed",
                ip_address=request.client.host,
                user_agent=request.headers.get("user-agent"),
                details=f"Failed login attempt for username: {user_credentials.username}"
            )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # Create tokens
        access_token_expires = timedelta(minutes=auth_manager.access_token_expire_minutes)
        token_data = {"sub": str(user.id), "username": user.username}
        
        access_token = auth_manager.create_access_token(
            data=token_data,
            expires_delta=access_token_expires
        )
        refresh_token = auth_manager.create_refresh_token(data=token_data)
        
        # Log successful login
        await auth_manager.log_user_action(
            db=db,
            user_id=user.id,
            action="login_success",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            details="Successful login"
        )
        
        logger.info("User logged in successfully", user_id=user.id, username=user.username)
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=auth_manager.access_token_expire_minutes * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Login failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_data: RefreshToken,
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """Refresh access token using refresh token"""
    try:
        from main import app
        auth_manager = app.state.auth_manager
        
        # Verify refresh token
        payload = auth_manager.verify_token(token_data.refresh_token, token_type="refresh")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        # Get user ID from payload
        user_id = payload.get("sub")
        username = payload.get("username")
        
        if not user_id or not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token payload"
            )
        
        # Verify user still exists and is active
        stmt = select(User).where(User.id == int(user_id), User.is_active == True)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Create new tokens
        access_token_expires = timedelta(minutes=auth_manager.access_token_expire_minutes)
        token_data_new = {"sub": str(user.id), "username": user.username}
        
        access_token = auth_manager.create_access_token(
            data=token_data_new,
            expires_delta=access_token_expires
        )
        refresh_token_new = auth_manager.create_refresh_token(data=token_data_new)
        
        # Log token refresh
        await auth_manager.log_user_action(
            db=db,
            user_id=user.id,
            action="token_refreshed",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            details="Access token refreshed"
        )
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token_new,
            expires_in=auth_manager.access_token_expire_minutes * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Token refresh failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )

@router.get("/profile", response_model=UserProfile)
async def get_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return UserProfile(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        is_admin=current_user.is_admin,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )

@router.post("/change-password")
async def change_password(
    password_data: ChangePassword,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Change user password"""
    try:
        from main import app
        auth_manager = app.state.auth_manager
        
        # Verify current password
        if not auth_manager.verify_password(password_data.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Validate new password strength
        if not validate_password_strength(password_data.new_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password does not meet security requirements"
            )
        
        # Update password
        current_user.hashed_password = auth_manager.get_password_hash(password_data.new_password)
        await db.commit()
        
        # Log password change
        await auth_manager.log_user_action(
            db=db,
            user_id=current_user.id,
            action="password_changed",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            details="User changed password"
        )
        
        logger.info("Password changed successfully", user_id=current_user.id)
        
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Password change failed", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )

@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Logout user (invalidate token on client side)"""
    try:
        from main import app
        auth_manager = app.state.auth_manager
        
        # Log logout
        await auth_manager.log_user_action(
            db=db,
            user_id=current_user.id,
            action="logout",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            details="User logged out"
        )
        
        logger.info("User logged out", user_id=current_user.id)
        
        return {"message": "Logged out successfully"}
        
    except Exception as e:
        logger.error("Logout failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )