"""Authentication API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import timedelta

from security.auth import (
    create_access_token,
    get_current_user,
    User,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from security.rbac import Role
from security.identity_verification import (
    initiate_email_verification,
    initiate_phone_verification,
    verify_code
)

router = APIRouter()


class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str
    expires_in: int


class UserRegistration(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str
    name: str
    role: Role
    phone: Optional[str] = None


class VerificationRequest(BaseModel):
    """Verification code request."""
    identifier: str  # email or phone
    code: str


class VerificationInitiate(BaseModel):
    """Initiate verification request."""
    email: Optional[EmailStr] = None
    phone: Optional[str] = None


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth 2.0 login endpoint.
    
    Returns JWT access token with 1-hour expiration.
    """
    # TODO: Implement actual user authentication against database
    # This is a placeholder implementation
    
    # Verify credentials (placeholder)
    # In production, hash password and check against database
    if not form_data.username or not form_data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "user_id": "user-123",  # Replace with actual user ID
            "email": form_data.username,
            "role": "technician"  # Replace with actual user role
        },
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60  # seconds
    }


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegistration):
    """
    Register new user.
    
    Requires email verification before account activation.
    """
    # TODO: Implement actual user registration
    # 1. Check if user already exists
    # 2. Hash password
    # 3. Create user in database
    # 4. Send verification email
    
    # Initiate email verification
    code = initiate_email_verification(user_data.email)
    
    if not code:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email"
        )
    
    return {
        "message": "Registration successful. Please check your email for verification code.",
        "email": user_data.email
    }


@router.post("/verify-email")
async def verify_email(verification: VerificationRequest):
    """
    Verify email address with verification code.
    """
    is_valid = verify_code(verification.identifier, verification.code)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code"
        )
    
    # TODO: Update user status in database to verified
    
    return {
        "message": "Email verified successfully",
        "verified": True
    }


@router.post("/verify-phone")
async def verify_phone(verification: VerificationRequest):
    """
    Verify phone number with verification code.
    """
    is_valid = verify_code(verification.identifier, verification.code)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code"
        )
    
    # TODO: Update user phone verification status in database
    
    return {
        "message": "Phone verified successfully",
        "verified": True
    }


@router.post("/initiate-verification")
async def initiate_verification(request: VerificationInitiate):
    """
    Initiate email or phone verification.
    """
    if request.email:
        code = initiate_email_verification(request.email)
        if code:
            return {
                "message": "Verification code sent to email",
                "method": "email"
            }
    
    if request.phone:
        code = initiate_phone_verification(request.phone)
        if code:
            return {
                "message": "Verification code sent to phone",
                "method": "sms"
            }
    
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to send verification code"
    )


@router.get("/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user information.
    """
    return current_user


@router.post("/refresh")
async def refresh_token(current_user: User = Depends(get_current_user)):
    """
    Refresh access token.
    
    Returns new JWT token with extended expiration.
    """
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "user_id": current_user.id,
            "email": current_user.email,
            "role": current_user.role
        },
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """
    Logout current user.
    
    In production, add token to blacklist or revoke in database.
    """
    # TODO: Implement token blacklist/revocation
    
    return {
        "message": "Logged out successfully"
    }
