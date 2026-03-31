"""OAuth 2.0 authentication with JWT tokens."""

from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
import os

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hour as per requirements

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class TokenData(BaseModel):
    """Token payload data."""
    user_id: str
    email: str
    role: str
    exp: datetime


class User(BaseModel):
    """User model for authentication."""
    id: str
    email: str
    role: str
    name: Optional[str] = None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token with 1-hour expiration.
    
    Args:
        data: Token payload data (user_id, email, role)
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def verify_access_token(token: str) -> TokenData:
    """
    Verify and decode JWT access token.
    
    Args:
        token: JWT token string
        
    Returns:
        TokenData with user information
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
        email: str = payload.get("email")
        role: str = payload.get("role")
        exp_timestamp = payload.get("exp")
        
        if user_id is None or email is None or role is None or exp_timestamp is None:
            raise credentials_exception
        
        exp: datetime = datetime.fromtimestamp(exp_timestamp)
            
        token_data = TokenData(
            user_id=user_id,
            email=email,
            role=role,
            exp=exp
        )
        
        return token_data
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (jwt.PyJWTError, jwt.DecodeError, Exception):
        raise credentials_exception


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Get current authenticated user from JWT token.
    
    Args:
        token: JWT token from Authorization header
        
    Returns:
        User object with authentication details
        
    Raises:
        HTTPException: If token is invalid
    """
    token_data = verify_access_token(token)
    
    user = User(
        id=token_data.user_id,
        email=token_data.email,
        role=token_data.role
    )
    
    return user


def create_oauth2_authorization_url(
    client_id: str,
    redirect_uri: str,
    scope: str = "openid profile email",
    state: Optional[str] = None
) -> str:
    """
    Create OAuth 2.0 authorization URL for external providers.
    
    Args:
        client_id: OAuth client ID
        redirect_uri: Callback URL after authentication
        scope: OAuth scopes to request
        state: Optional state parameter for CSRF protection
        
    Returns:
        Authorization URL string
    """
    # This is a placeholder for OAuth 2.0 provider integration
    # In production, integrate with providers like Google, Microsoft, etc.
    base_url = os.getenv("OAUTH_PROVIDER_URL", "https://oauth.example.com/authorize")
    
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
    }
    
    if state:
        params["state"] = state
    
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    return f"{base_url}?{query_string}"


def exchange_code_for_token(code: str, redirect_uri: str) -> dict:
    """
    Exchange OAuth authorization code for access token.
    
    Args:
        code: Authorization code from OAuth provider
        redirect_uri: Redirect URI used in authorization request
        
    Returns:
        Token response with access_token, refresh_token, etc.
    """
    # This is a placeholder for OAuth 2.0 token exchange
    # In production, make HTTP request to provider's token endpoint
    raise NotImplementedError("OAuth 2.0 token exchange not yet implemented")
