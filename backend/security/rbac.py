"""Role-Based Access Control (RBAC) implementation."""

from enum import Enum
from typing import List, Set
from fastapi import HTTPException, status, Depends
from functools import wraps

from .auth import User, get_current_user


class Role(str, Enum):
    """User roles in the system."""
    TECHNICIAN = "technician"
    DISPATCHER = "dispatcher"
    CUSTOMER = "customer"
    ADMIN = "admin"


class Permission(str, Enum):
    """System permissions."""
    READ_JOBS = "read-jobs"
    WRITE_JOBS = "write-jobs"
    ACCESS_REPORTS = "access-reports"
    MANAGE_USERS = "manage-users"
    READ_INVENTORY = "read-inventory"
    WRITE_INVENTORY = "write-inventory"
    ACCESS_DIAGNOSTICS = "access-diagnostics"
    MANAGE_SCHEDULE = "manage-schedule"
    VIEW_ANALYTICS = "view-analytics"
    MANAGE_SYSTEM = "manage-system"


# Role-Permission mapping
ROLE_PERMISSIONS: dict[Role, Set[Permission]] = {
    Role.CUSTOMER: {
        Permission.READ_JOBS,  # Can view their own jobs
    },
    Role.TECHNICIAN: {
        Permission.READ_JOBS,
        Permission.WRITE_JOBS,
        Permission.READ_INVENTORY,
        Permission.ACCESS_DIAGNOSTICS,
    },
    Role.DISPATCHER: {
        Permission.READ_JOBS,
        Permission.WRITE_JOBS,
        Permission.ACCESS_REPORTS,
        Permission.READ_INVENTORY,
        Permission.WRITE_INVENTORY,
        Permission.MANAGE_SCHEDULE,
        Permission.VIEW_ANALYTICS,
    },
    Role.ADMIN: {
        Permission.READ_JOBS,
        Permission.WRITE_JOBS,
        Permission.ACCESS_REPORTS,
        Permission.MANAGE_USERS,
        Permission.READ_INVENTORY,
        Permission.WRITE_INVENTORY,
        Permission.ACCESS_DIAGNOSTICS,
        Permission.MANAGE_SCHEDULE,
        Permission.VIEW_ANALYTICS,
        Permission.MANAGE_SYSTEM,
    },
}


def get_role_permissions(role: Role) -> Set[Permission]:
    """
    Get all permissions for a given role.
    
    Args:
        role: User role
        
    Returns:
        Set of permissions for the role
    """
    return ROLE_PERMISSIONS.get(role, set())


def check_permission(user: User, required_permission: Permission) -> bool:
    """
    Check if user has a specific permission.
    
    Args:
        user: User object with role
        required_permission: Permission to check
        
    Returns:
        True if user has permission, False otherwise
    """
    try:
        user_role = Role(user.role)
    except ValueError:
        return False
    
    user_permissions = get_role_permissions(user_role)
    return required_permission in user_permissions


def require_permission(required_permission: Permission):
    """
    Decorator to require specific permission for endpoint access.
    
    Args:
        required_permission: Permission required to access endpoint
        
    Returns:
        Decorator function
        
    Raises:
        HTTPException: If user lacks required permission
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_user), **kwargs):
            if not check_permission(current_user, required_permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {required_permission.value} required"
                )
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator


def require_role(required_role: Role):
    """
    Decorator to require specific role for endpoint access.
    
    Args:
        required_role: Role required to access endpoint
        
    Returns:
        Decorator function
        
    Raises:
        HTTPException: If user doesn't have required role
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_user), **kwargs):
            try:
                user_role = Role(current_user.role)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid user role"
                )
            
            if user_role != required_role and user_role != Role.ADMIN:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role {required_role.value} required"
                )
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator


def require_any_role(required_roles: List[Role]):
    """
    Decorator to require any of the specified roles for endpoint access.
    
    Args:
        required_roles: List of roles, any of which grants access
        
    Returns:
        Decorator function
        
    Raises:
        HTTPException: If user doesn't have any of the required roles
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_user), **kwargs):
            try:
                user_role = Role(current_user.role)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid user role"
                )
            
            if user_role not in required_roles and user_role != Role.ADMIN:
                roles_str = ", ".join([r.value for r in required_roles])
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"One of these roles required: {roles_str}"
                )
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator
