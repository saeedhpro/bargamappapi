from typing import List

from fastapi import APIRouter, Depends, Query

from api.deps import get_current_admin
from models.role import Role
from models.user import User
from schemas.user import UsersListOut, UserAdminOut, CreateUserIn, RoleOut

router = APIRouter(
    prefix="/api/v1/admin/roles",
    tags=["AdminRoles"]
)


@router.get("/", response_model=List[RoleOut])
async def list_roles(admin=Depends(get_current_admin)):
    roles = await Role.filter(is_active=True).order_by("id")
    return roles
