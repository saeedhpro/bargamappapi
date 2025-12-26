from fastapi import APIRouter, Query, HTTPException, Depends, Request
from tortoise.expressions import Q
from typing import List, Optional

from api.deps import get_current_user
from models.garden import UserGarden
from models.history import PlantHistory
from models.user import User
from schemas.history import PlantHistoryResponse, PlantHistoryListOut

router = APIRouter(prefix="/api/v1/admin/history", tags=["History"])


@router.get("/", response_model=PlantHistoryListOut)
async def get_plants_history(
    request: Request,
    page: int = Query(1, ge=1, description="شماره صفحه"),
    limit: int = Query(20, ge=1, le=100, description="تعداد آیتم در هر صفحه"),
    search: Optional[str] = Query(None, description="جستجو در نام فارسی یا علمی"),
    current_user: User = Depends(get_current_user),
):
    offset = (page - 1) * limit

    try:
        query = PlantHistory.filter(
            Q(image_path__isnull=False) & ~Q(image_path="")
        )
        if search:
            query = query.filter(
                Q(plant_name__icontains=search)
                | Q(common_name__icontains=search)
            )

        # 📊 شمارش کل
        total = await query.count()

        # 📄 گرفتن آیتم‌های این صفحه
        plants = await query.order_by("-created_at").offset(offset).limit(limit)

        base_url = str(request.base_url).rstrip("/")
        results: List[PlantHistoryResponse] = []

        for plant in plants:
            # ساخت URL عکس اصلی
            if plant.image_path:
                full_image_url = (
                    plant.image_path
                    if plant.image_path.startswith("http")
                    else f"{base_url}/{plant.image_path.lstrip('/')}"
                )
            else:
                full_image_url = None

            # گالری تصاویر
            full_gallery = []
            if plant.image_paths:
                for p in plant.image_paths:
                    full_gallery.append(
                        p if p.startswith("http") else f"{base_url}/{p.lstrip('/')}"
                    )

            # جایگزینی داده‌های ناسازگار (null)
            details = plant.details or {}
            diseases = normalize_text(details.get("diseases"))
            pest_control = normalize_text(details.get("pest_control"))

            results.append(
                PlantHistoryResponse(
                    id=plant.id,
                    plant_name=plant.plant_name,
                    common_name=plant.common_name,
                    image_path=full_image_url,
                    details=plant.details if plant.details else {},
                    created_at=plant.created_at,
                    accuracy=plant.accuracy,
                    description=plant.description or "",
                    in_garden=False,
                    garden_id=None,
                    image_paths=full_gallery,
                    diseases=diseases,
                    pest_control=pest_control,
                )
            )

        return PlantHistoryListOut(
            total=total,
            page=page,
            page_size=limit,
            items=results,
        )

    except Exception as e:
        print(f"❌ Error fetching history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def normalize_text(val):
    if isinstance(val, dict):
        return "\n".join(f"{k}: {v}" for k, v in val.items())
    return val
