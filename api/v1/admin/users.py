from fastapi import APIRouter, Depends

from api.deps import get_current_admin
from models.user import User

router = APIRouter(
    prefix="/api/v1/admin/users",
    tags=["AdminUsers"]
)


@router.get("/")
async def list_users(admin=Depends(get_current_admin)):
    return await User.all()
