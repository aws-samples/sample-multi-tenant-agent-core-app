"""
Admin Authentication Service
Manages admin user privileges and tenant-specific admin access
"""

from fastapi import HTTPException, Depends
from typing import Dict, List
import boto3
import os
from app.auth import get_current_user

class AdminAuthService:
    """Admin authentication using Cognito Groups"""
    
    def __init__(self):
        self.cognito_client = boto3.client('cognito-idp')
        self.user_pool_id = os.getenv("COGNITO_USER_POOL_ID")
    
    def is_tenant_admin(self, user_context: Dict[str, str], tenant_id: str) -> bool:
        """Check if user is admin using Cognito Groups"""
        # Check cognito:groups claim in JWT
        user_groups = user_context.get("cognito:groups", [])
        user_tenant = user_context.get("tenant_id", "")
        
        # Must be same tenant and in admin group
        admin_group = f"{tenant_id}-admins"
        return user_tenant == tenant_id and admin_group in user_groups
    
    def get_admin_tenants(self, user_groups: List[str]) -> List[str]:
        """Get list of tenants where user has admin access from Cognito groups"""
        admin_tenants = []
        for group in user_groups:
            if group.endswith('-admins'):
                tenant_id = group.replace('-admins', '')
                admin_tenants.append(tenant_id)
        return admin_tenants

# Admin dependency for FastAPI endpoints
async def get_admin_user(current_user: dict = Depends(get_current_user)) -> Dict:
    """Dependency to verify admin access using Cognito Groups"""
    admin_service = AdminAuthService()
    
    user_groups = current_user.get("cognito:groups", [])
    admin_tenants = admin_service.get_admin_tenants(user_groups)
    
    if not admin_tenants:
        raise HTTPException(status_code=403, detail="Admin access required - no admin groups found")
    
    return {
        **current_user,
        "admin_tenants": admin_tenants,
        "admin_groups": user_groups,
        "is_admin": True
    }

async def verify_tenant_admin(tenant_id: str, current_user: dict = Depends(get_current_user)) -> Dict:
    """Verify admin access for specific tenant"""
    admin_service = AdminAuthService()
    
    if not admin_service.is_tenant_admin(current_user, tenant_id):
        raise HTTPException(
            status_code=403, 
            detail=f"Admin access required for tenant {tenant_id}"
        )
    
    return current_user