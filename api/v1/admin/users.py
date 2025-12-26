from fastapi import APIRouter, Depends, Query, HTTPException

from api.deps import get_current_admin
from models.role import Role
from models.user import User
from schemas.user import UsersListOut, UserAdminOut, CreateUserIn

router = APIRouter(
    prefix="/api/v1/admin/users",
    tags=["AdminUsers"]
)


@router.get("/", response_model=UsersListOut)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, le=50),
    admin=Depends(get_current_admin)
):
    offset = (page - 1) * page_size

    total = await User.all().count()
    users = (
        await User.all()
        .prefetch_related("role")
        .offset(offset)
        .limit(page_size)
        .order_by("-created_at")
    )
    items = [
        UserAdminOut(
            id=u.id,
            phone=u.phone,
            full_name=None,
            role=u.role,
            identified_plants_count=0,
            is_active=u.is_active,
            created_at=u.created_at,
        )
        for u in users
    ]

    return UsersListOut(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )


@router.post("/", response_model=UserAdminOut)
async def create_user(data: CreateUserIn, admin=Depends(get_current_admin)):
    role = await Role.get(id=data.role_id)
    user = await User.create(
        phone=data.phone,
        role=role
    )
    return UserAdminOut(
        id=user.id,
        phone=user.phone,
        full_name=None,
        role=role,
        identified_plants_count=0,
        is_active=user.is_active,
        created_at=user.created_at,
    )



@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_admin),
):
    if user_id == 1:
        raise HTTPException(400, "این کاربر قابل حذف نیست")

    user = await User.get_or_none(id=user_id).prefetch_related("role")
    if not user:
        raise HTTPException(404, "کاربر یافت نشد")

    # ❌ حذف خود ادمین
    if user.id == current_user.id:
        raise HTTPException(403, "امکان حذف حساب خودتان وجود ندارد")

    # ❌ حذف سایر ادمین‌ها
    if user.role.name == "admin":
        raise HTTPException(403, "امکان حذف مدیر دیگر وجود ندارد")

    await user.delete()
    return {"success": True}
