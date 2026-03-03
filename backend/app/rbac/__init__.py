"""
RBAC (Role-Based Access Control) Module for OpenMaritime.

Defines roles, permissions, and enforcement for multi-tenant access control.
"""
from enum import Enum
from typing import Set, Dict, List, Optional
from functools import wraps
from fastapi import HTTPException, Depends
from uuid import UUID


class Role(str, Enum):
    """Available roles in the system"""
    ADMIN = "admin"
    BROKER = "broker"
    OWNER = "owner"
    CHARTERER = "charterer"
    ANALYST = "analyst"
    APPROVER = "approver"
    VIEWER = "viewer"


class Permission(str, Enum):
    """Granular permissions"""
    # Fixtures
    FIXTURE_READ = "fixture:read"
    FIXTURE_CREATE = "fixture:create"
    FIXTURE_UPDATE = "fixture:update"
    FIXTURE_DELETE = "fixture:delete"
    FIXTURE_ENRICH = "fixture:enrich"
    FIXTURE_RANK = "fixture:rank"
    FIXTURE_DECIDE = "fixture:decide"
    
    # Users & Access
    USER_READ = "user:read"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_INVITE = "user:invite"
    
    # Plugins
    PLUGIN_READ = "plugin:read"
    PLUGIN_CONFIGURE = "plugin:configure"
    PLUGIN_ENABLE = "plugin:enable"
    PLUGIN_DISABLE = "plugin:disable"
    
    # Settings
    SETTINGS_READ = "settings:read"
    SETTINGS_UPDATE = "settings:update"
    
    # API Keys
    APIKEY_READ = "apikey:read"
    APIKEY_CREATE = "apikey:create"
    APIKEY_DELETE = "apikey:delete"
    
    # Email
    EMAIL_READ = "email:read"
    EMAIL_SYNC = "email:sync"
    EMAIL_DELETE = "email:delete"
    
    # Voice Notes
    VOICE_CREATE = "voice:create"
    VOICE_TRANSCRIBE = "voice:transcribe"
    
    # Reports & Analytics
    REPORT_READ = "report:read"
    REPORT_EXPORT = "report:export"
    
    # Admin
    ADMIN_AUDIT = "admin:audit"
    ADMIN_SSO = "admin:sso"
    ADMIN_BILLING = "admin:billing"


# Role -> Permissions mapping
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ADMIN: {
        # Full access
        Permission.FIXTURE_READ, Permission.FIXTURE_CREATE, Permission.FIXTURE_UPDATE, Permission.FIXTURE_DELETE,
        Permission.FIXTURE_ENRICH, Permission.FIXTURE_RANK, Permission.FIXTURE_DECIDE,
        Permission.USER_READ, Permission.USER_CREATE, Permission.USER_UPDATE, Permission.USER_DELETE, Permission.USER_INVITE,
        Permission.PLUGIN_READ, Permission.PLUGIN_CONFIGURE, Permission.PLUGIN_ENABLE, Permission.PLUGIN_DISABLE,
        Permission.SETTINGS_READ, Permission.SETTINGS_UPDATE,
        Permission.APIKEY_READ, Permission.APIKEY_CREATE, Permission.APIKEY_DELETE,
        Permission.EMAIL_READ, Permission.EMAIL_SYNC, Permission.EMAIL_DELETE,
        Permission.VOICE_CREATE, Permission.VOICE_TRANSCRIBE,
        Permission.REPORT_READ, Permission.REPORT_EXPORT,
        Permission.ADMIN_AUDIT, Permission.ADMIN_SSO, Permission.ADMIN_BILLING,
    },
    Role.BROKER: {
        Permission.FIXTURE_READ, Permission.FIXTURE_CREATE, Permission.FIXTURE_UPDATE,
        Permission.FIXTURE_ENRICH, Permission.FIXTURE_RANK, Permission.FIXTURE_DECIDE,
        Permission.PLUGIN_READ,
        Permission.SETTINGS_READ,
        Permission.APIKEY_READ, Permission.APIKEY_CREATE,
        Permission.EMAIL_READ, Permission.EMAIL_SYNC,
        Permission.VOICE_CREATE, Permission.VOICE_TRANSCRIBE,
        Permission.REPORT_READ, Permission.REPORT_EXPORT,
    },
    Role.OWNER: {
        Permission.FIXTURE_READ, Permission.FIXTURE_UPDATE,
        Permission.PLUGIN_READ,
        Permission.SETTINGS_READ,
        Permission.EMAIL_READ,
        Permission.REPORT_READ, Permission.REPORT_EXPORT,
    },
    Role.CHARTERER: {
        Permission.FIXTURE_READ, Permission.FIXTURE_CREATE,
        Permission.PLUGIN_READ,
        Permission.SETTINGS_READ,
        Permission.EMAIL_READ, Permission.EMAIL_SYNC,
        Permission.REPORT_READ, Permission.REPORT_EXPORT,
    },
    Role.ANALYST: {
        Permission.FIXTURE_READ,
        Permission.PLUGIN_READ,
        Permission.SETTINGS_READ,
        Permission.EMAIL_READ,
        Permission.REPORT_READ, Permission.REPORT_EXPORT,
    },
    Role.APPROVER: {
        Permission.FIXTURE_READ, Permission.FIXTURE_UPDATE,
        Permission.USER_READ,
        Permission.PLUGIN_READ,
        Permission.SETTINGS_READ,
        Permission.REPORT_READ, Permission.REPORT_EXPORT,
    },
    Role.VIEWER: {
        Permission.FIXTURE_READ,
        Permission.SETTINGS_READ,
        Permission.EMAIL_READ,
        Permission.REPORT_READ,
    },
}


class RBACService:
    """
    Centralized RBAC service for permission checking.
    """
    
    def __init__(self):
        self._cache: Dict[str, Set[Permission]] = {}
    
    def get_role_permissions(self, role: Role) -> Set[Permission]:
        """Get all permissions for a role"""
        return ROLE_PERMISSIONS.get(role, set()).copy()
    
    def has_permission(self, role: Role, permission: Permission) -> bool:
        """Check if a role has a specific permission"""
        return permission in ROLE_PERMISSIONS.get(role, set())
    
    def has_any_permission(self, role: Role, permissions: List[Permission]) -> bool:
        """Check if role has any of the specified permissions"""
        role_perms = ROLE_PERMISSIONS.get(role, set())
        return any(p in role_perms for p in permissions)
    
    def has_all_permissions(self, role: Role, permissions: List[Permission]) -> bool:
        """Check if role has all specified permissions"""
        role_perms = ROLE_PERMISSIONS.get(role, set())
        return all(p in role_perms for p in permissions)
    
    def get_user_permissions(self, user) -> Set[Permission]:
        """Get effective permissions for a user based on their role"""
        if not user:
            return set()
        
        # If user is superuser, give all permissions
        if getattr(user, 'is_superuser', False):
            all_perms = set()
            for perms in ROLE_PERMISSIONS.values():
                all_perms.update(perms)
            return all_perms
        
        # Get role from user
        user_role = getattr(user, 'role', None)
        if user_role:
            try:
                role = Role(user_role)
                return self.get_role_permissions(role)
            except ValueError:
                pass
        
        # Default to viewer
        return self.get_role_permissions(Role.VIEWER)
    
    def authorize(self, role: Role, required_permissions: List[Permission]):
        """Decorator for endpoint authorization"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                if not self.has_any_permission(role, required_permissions):
                    raise HTTPException(
                        status_code=403,
                        detail=f"Missing required permissions: {required_permissions}"
                    )
                return await func(*args, **kwargs)
            return wrapper
        return decorator


rbac_service = RBACService()


async def get_current_user_role(user) -> Role:
    """Extract role from user object"""
    if not user:
        return Role.VIEWER
    
    if getattr(user, 'is_superuser', False):
        return Role.ADMIN
    
    user_role = getattr(user, 'role', None)
    if user_role:
        try:
            return Role(user_role)
        except ValueError:
            pass
    
    return Role.VIEWER


def require_permissions(permissions: List[Permission]):
    """FastAPI dependency for permission checking"""
    async def dependency(user = None):
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        user_perms = rbac_service.get_user_permissions(user)
        if not any(p in user_perms for p in permissions):
            raise HTTPException(
                status_code=403,
                detail=f"Missing required permissions: {permissions}"
            )
        return user
    return dependency


def require_role(role: Role):
    """FastAPI dependency for role checking"""
    async def dependency(user = None):
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        user_role = await get_current_user_role(user)
        if user_role != role and user_role != Role.ADMIN:
            raise HTTPException(
                status_code=403,
                detail=f"Requires role: {role.value}"
            )
        return user
    return dependency
