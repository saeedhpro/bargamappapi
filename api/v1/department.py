from fastapi import APIRouter, Depends, HTTPException
from api.deps import get_current_user, require_role
from models.user import User
from services.department_service import DepartmentService

router = APIRouter(prefix="/api/v1/departments", tags=["Departments"])


@router.get("")
async def list_departments(
        active_only: bool = True,
        service: DepartmentService = Depends()
):
    """دریافت لیست دپارتمان‌ها (عمومی)"""
    return {"departments": await service.get_all_departments(active_only)}


@router.post("")
async def create_department(
        payload: dict,
        service: DepartmentService = Depends(),
        current_user: User = Depends(require_role(["admin"]))
):
    """ایجاد دپارتمان جدید (فقط ادمین)"""
    name = payload.get("name")

    if not name:
        raise HTTPException(400, "نام دپارتمان الزامی است")

    dept = await service.create_department(name)
    return {"department": dept}


@router.put("/{dept_id}")
async def update_department(
        dept_id: int,
        payload: dict,
        service: DepartmentService = Depends(),
        current_user: User = Depends(require_role(["admin"]))
):
    """به‌روزرسانی دپارتمان (فقط ادمین)"""
    dept = await service.update_department(
        dept_id,
        name=payload.get("name"),
        is_active=payload.get("is_active")
    )

    return {"department": dept}


@router.delete("/{dept_id}")
async def delete_department(
        dept_id: int,
        service: DepartmentService = Depends(),
        current_user: User = Depends(require_role(["admin"]))
):
    """حذف دپارتمان (فقط ادمین)"""
    success = await service.delete_department(dept_id)

    if not success:
        raise HTTPException(
            400,
            "این دپارتمان دارای مکالمات فعال است و قابل حذف نیست"
        )

    return {"message": "دپارتمان با موفقیت حذف شد"}
