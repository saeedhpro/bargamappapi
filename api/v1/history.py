from fastapi import APIRouter, Query, HTTPException, Depends
from tortoise.expressions import Q
from typing import List

from models.history import PlantHistory
from schemas.history import PlantHistoryResponse

router = APIRouter(prefix="/api/v1/garden", tags=["History"])


@router.get("/history", response_model=List[PlantHistoryResponse])
async def get_plants_history(
        page: int = Query(1, ge=1, description="شماره صفحه"),
        limit: int = Query(20, ge=1, le=100, description="تعداد آیتم در هر صفحه"),
        search: str = Query(None, description="جستجو در نام فارسی یا علمی"),
        # current_user: User = Depends(get_current_user)
):
    offset = (page - 1) * limit

    # 1. شروع کوئری
    # اگر فقط برای کاربر جاری است: PlantHistory.filter(user=current_user)
    query = PlantHistory.all()

    if search:
        query = query.filter(
            Q(plant_name__icontains=search) |
            Q(common_name__icontains=search)
        )

    # order_by('-created_at'): جدیدترین‌ها اول باشند prefetch_related: اگر نیاز به اطلاعات یوزر داشتید (اینجا لازم
    # نیست ولی برای پرفرمنس خوبه اگر فیلد ریلیشنال بخواهید)

    try:
        plants = await query.order_by('-created_at').offset(offset).limit(limit)
        return plants

    except Exception as e:
        print(f"Error fetching history: {e}")
        raise HTTPException(status_code=500, detail="خطا در دریافت تاریخچه گیاهان")
