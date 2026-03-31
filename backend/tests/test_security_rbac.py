"""Unit tests for RBAC module."""

import pytest
from fastapi import HTTPException

from security.rbac import (
    Role,
    Permission,
    get_role_permissions,
    check_permission,
)
from security.auth import User


def test_role_enum():
    """Test Role enum values."""
    assert Role.TECHNICIAN.value == "technician"
    assert Role.DISPATCHER.value == "dispatcher"
    assert Role.CUSTOMER.value == "customer"
    assert Role.ADMIN.value == "admin"


def test_permission_enum():
    """Test Permission enum values."""
    assert Permission.READ_JOBS.value == "read-jobs"
    assert Permission.WRITE_JOBS.value == "write-jobs"
    assert Permission.ACCESS_REPORTS.value == "access-reports"
    assert Permission.MANAGE_USERS.value == "manage-users"


def test_get_role_permissions_technician():
    """Test permissions for technician role."""
    permissions = get_role_permissions(Role.TECHNICIAN)
    
    assert Permission.READ_JOBS in permissions
    assert Permission.WRITE_JOBS in permissions
    assert Permission.READ_INVENTORY in permissions
    assert Permission.ACCESS_DIAGNOSTICS in permissions
    assert Permission.MANAGE_USERS not in permissions


def test_get_role_permissions_dispatcher():
    """Test permissions for dispatcher role."""
    permissions = get_role_permissions(Role.DISPATCHER)
    
    assert Permission.READ_JOBS in permissions
    assert Permission.WRITE_JOBS in permissions
    assert Permission.ACCESS_REPORTS in permissions
    assert Permission.MANAGE_SCHEDULE in permissions
    assert Permission.MANAGE_USERS not in permissions


def test_get_role_permissions_customer():
    """Test permissions for customer role."""
    permissions = get_role_permissions(Role.CUSTOMER)
    
    assert Permission.READ_JOBS in permissions
    assert Permission.WRITE_JOBS not in permissions
    assert Permission.MANAGE_USERS not in permissions


def test_get_role_permissions_admin():
    """Test permissions for admin role."""
    permissions = get_role_permissions(Role.ADMIN)
    
    assert Permission.READ_JOBS in permissions
    assert Permission.WRITE_JOBS in permissions
    assert Permission.ACCESS_REPORTS in permissions
    assert Permission.MANAGE_USERS in permissions
    assert Permission.MANAGE_SYSTEM in permissions


def test_check_permission_technician_can_read_jobs():
    """Test technician can read jobs."""
    user = User(id="tech-1", email="tech@example.com", role="technician")
    
    assert check_permission(user, Permission.READ_JOBS) is True


def test_check_permission_technician_cannot_manage_users():
    """Test technician cannot manage users."""
    user = User(id="tech-1", email="tech@example.com", role="technician")
    
    assert check_permission(user, Permission.MANAGE_USERS) is False


def test_check_permission_customer_can_read_jobs():
    """Test customer can read jobs."""
    user = User(id="cust-1", email="customer@example.com", role="customer")
    
    assert check_permission(user, Permission.READ_JOBS) is True


def test_check_permission_customer_cannot_write_jobs():
    """Test customer cannot write jobs."""
    user = User(id="cust-1", email="customer@example.com", role="customer")
    
    assert check_permission(user, Permission.WRITE_JOBS) is False


def test_check_permission_admin_has_all_permissions():
    """Test admin has all permissions."""
    user = User(id="admin-1", email="admin@example.com", role="admin")
    
    assert check_permission(user, Permission.READ_JOBS) is True
    assert check_permission(user, Permission.WRITE_JOBS) is True
    assert check_permission(user, Permission.MANAGE_USERS) is True
    assert check_permission(user, Permission.MANAGE_SYSTEM) is True


def test_check_permission_invalid_role():
    """Test permission check with invalid role."""
    user = User(id="user-1", email="user@example.com", role="invalid_role")
    
    assert check_permission(user, Permission.READ_JOBS) is False


def test_dispatcher_can_manage_schedule():
    """Test dispatcher can manage schedule."""
    user = User(id="disp-1", email="dispatcher@example.com", role="dispatcher")
    
    assert check_permission(user, Permission.MANAGE_SCHEDULE) is True


def test_dispatcher_cannot_manage_users():
    """Test dispatcher cannot manage users."""
    user = User(id="disp-1", email="dispatcher@example.com", role="dispatcher")
    
    assert check_permission(user, Permission.MANAGE_USERS) is False
