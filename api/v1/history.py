from fastapi import APIRouter, Query, HTTPException, Depends, Request
from tortoise.expressions import Q
from typing import List

from models.history import PlantHistory
from schemas.history import PlantHistoryResponse

router = APIRouter(prefix="/api/v1/garden", tags=["History"])


@router.get("/history", response_model=List[PlantHistoryResponse])
async def get_plants_history(
        request: Request,
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

    try:
        plants = await query.order_by('-created_at').offset(offset).limit(limit)

        # 2. ساخت base_url برای تصاویر
        base_url = str(request.base_url).rstrip('/')
        results = []

        for plant in plants:
            # 3. تبدیل آدرس نسبی به مطلق
            full_image_url = None
            if plant.image_path:
                if not plant.image_path.startswith('http'):
                    clean_path = plant.image_path.lstrip('/')
                    full_image_url = f"{base_url}/{clean_path}"
                else:
                    full_image_url = plant.image_path

            # 4. ساخت response با URL کامل
            results.append(PlantHistoryResponse(
                id=plant.id,
                plant_name=plant.plant_name,
                common_name=plant.common_name,
                image_path=full_image_url,
                details=plant.details if plant.details else {},
                created_at=plant.created_at
            ))

        return results

    except Exception as e:
        print(f"Error fetching history: {e}")
        raise HTTPException(status_code=500, detail="خطا در دریافت تاریخچه گیاهان")
