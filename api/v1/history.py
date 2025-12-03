from fastapi import APIRouter, Query, HTTPException, Depends, Request
from tortoise.expressions import Q
from typing import List

from api.deps import get_current_user
from models.garden import UserGarden
from models.history import PlantHistory
from models.user import User
from schemas.history import PlantHistoryResponse

router = APIRouter(prefix="/api/v1/garden", tags=["History"])


@router.get("/history", response_model=List[PlantHistoryResponse])
async def get_plants_history(
        request: Request,
        page: int = Query(1, ge=1, description="شماره صفحه"),
        limit: int = Query(20, ge=1, le=100, description="تعداد آیتم در هر صفحه"),
        search: str = Query(None, description="جستجو در نام فارسی یا علمی"),
        current_user: User = Depends(get_current_user)
):
    offset = (page - 1) * limit

    query = PlantHistory.all()
    query = query.filter(
        Q(image_path__isnull=False) & ~Q(image_path="")
    )
    if search:
        query = query.filter(
            Q(plant_name__icontains=search) |
            Q(common_name__icontains=search)
        )

    try:
        plants = await query.order_by('-created_at').offset(offset).limit(limit)

        base_url = str(request.base_url).rstrip('/')
        results = []

        for plant in plants:
            # 1. مدیریت آدرس عکس
            full_image_url = None
            if plant.image_path:
                if not plant.image_path.startswith('http'):
                    clean_path = plant.image_path.lstrip('/')
                    full_image_url = f"{base_url}/{clean_path}"
                else:
                    full_image_url = plant.image_path
            full_gallery = []
            if plant.image_paths:
                for p in plant.image_paths:
                    if p.startswith("http"):
                        full_gallery.append(p)
                    else:
                        clean_path = p.lstrip("/")
                        full_gallery.append(f"{base_url}/{clean_path}")

            garden_item = await UserGarden.filter(
                user=current_user,
                origin_history_id=plant.id
            ).order_by("-id").first()

            in_garden = garden_item is not None
            garden_id = garden_item.id if garden_item else None
            results.append(PlantHistoryResponse(
                id=plant.id,
                plant_name=plant.plant_name,
                common_name=plant.common_name,
                image_path=full_image_url,
                details=plant.details if plant.details else {},
                created_at=plant.created_at,
                accuracy=plant.accuracy,
                description=plant.description if plant.description else "",
                in_garden=in_garden,
                garden_id=garden_id,
                image_paths=full_gallery
            ))

        return results

    except Exception as e:
        print(f"Error fetching history: {e}")
        raise HTTPException(status_code=500, detail="خطا در دریافت تاریخچه گیاهان")
