from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import User, AuditLog
from database.connection import get_db_session
from config import settings

logger = structlog.get_logger(__name__)
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthManager:
    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = settings.REFRESH_TOKEN_EXPIRE_DAYS

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)

    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def verify_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check token type
            if payload.get("type") != token_type:
                return None
                
            # Check expiration
            exp_timestamp = payload.get("exp")
            if exp_timestamp and datetime.utcnow() > datetime.fromtimestamp(exp_timestamp):
                return None
                
            return payload
        except JWTError as e:
            logger.warning("JWT verification failed", error=str(e))
            return None

    async def authenticate_user(self, username: str, password: str, db: AsyncSession) -> Optional[User]:
        """Authenticate user with username/password"""
        try:
            stmt = select(User).where(User.username == username, User.is_active == True)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                logger.warning("Authentication failed: user not found", username=username)
                return None
            
            if not self.verify_password(password, user.hashed_password):
                logger.warning("Authentication failed: invalid password", username=username)
                return None
            
            # Update last login
            user.last_login = datetime.utcnow()
            await db.commit()
            
            logger.info("User authenticated successfully", user_id=user.id, username=username)
            return user
            
        except Exception as e:
            logger.error("Authentication error", error=str(e))
            return None

    async def get_current_user(self, credentials: HTTPAuthorizationCredentials, db: AsyncSession) -> User:
        """Get current user from JWT token"""
        token = credentials.credentials
        
        # Verify token
        payload = self.verify_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user ID from payload
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Fetch user from database
        try:
            stmt = select(User).where(User.id == int(user_id), User.is_active == True)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            return user
            
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user ID in token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            logger.error("Error fetching user", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    async def require_admin(self, current_user: User) -> User:
        """Require admin privileges"""
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
        return current_user

    async def log_user_action(
        self, 
        db: AsyncSession, 
        user_id: Optional[int], 
        action: str, 
        resource: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[str] = None
    ):
        """Log user action for audit trail"""
        try:
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource=resource,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details,
                timestamp=datetime.utcnow()
            )
            db.add(audit_log)
            await db.commit()
            
            logger.info(
                "User action logged",
                user_id=user_id,
                action=action,
                resource=resource,
                resource_id=resource_id
            )
        except Exception as e:
            logger.error("Failed to log user action", error=str(e))

# Dependency functions for FastAPI
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> User:
    """FastAPI dependency to get current user"""
    from main import app
    auth_manager = app.state.auth_manager
    return await auth_manager.get_current_user(credentials, db)

async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """FastAPI dependency to get current admin user"""
    from main import app
    auth_manager = app.state.auth_manager
    return await auth_manager.require_admin(current_user)

# Optional authentication (for public endpoints that can benefit from user context)
async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> Optional[User]:
    """FastAPI dependency to get current user (optional)"""
    if not credentials:
        return None
    
    try:
        from main import app
        auth_manager = app.state.auth_manager
        return await auth_manager.get_current_user(credentials, db)
    except HTTPException:
        return None