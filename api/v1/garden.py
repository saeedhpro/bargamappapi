from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, Depends, Request
from tortoise.expressions import Q

from api.deps import get_current_user
from models.garden import UserGarden
from models.history import PlantHistory
from models.user import User
from schemas.garden import AddFromHistoryRequest, GardenListResponse

router = APIRouter(prefix="/api/v1/garden", tags=["Garden"])


@router.post("/add")
async def add_from_history(
        req: AddFromHistoryRequest,
        current_user: User = Depends(get_current_user)
):
    # ابتدا گیاه مرجع را از تاریخچه پیدا می‌کنیم
    source_plant = await PlantHistory.get_or_none(id=req.history_id)

    if not source_plant:
        raise HTTPException(status_code=404, detail="گیاه مورد نظر در تاریخچه یافت نشد")

    # --- بخش جدید: بررسی وجود گیاه در باغچه کاربر ---
    # 1. بررسی اینکه آیا این گیاه قبلاً به باغچه اضافه شده است یا خیر
    existing_garden_item = await UserGarden.get_or_none(
        user=current_user,
        plant_name=source_plant.plant_name
    )

    # 2. اگر گیاه از قبل در باغچه وجود دارد، خطای 409 (Conflict) برگردان
    if existing_garden_item:
        raise HTTPException(
            status_code=409,  # 409 Conflict: درخواست معتبر است اما به دلیل وضعیت فعلی منبع، قابل انجام نیست
            detail={
                "message": "این گیاه از قبل در باغچه شما وجود دارد.",
                "garden_id": existing_garden_item.id
            }
        )

    # اگر گیاه در باغچه نبود، آن را ایجاد می‌کنیم
    new_garden_item = await UserGarden.create(
        user=current_user,
        plant_name=source_plant.plant_name,
        nickname=req.nickname or source_plant.common_name,
        image_path=source_plant.image_path,
        image_paths=source_plant.image_paths,
        details=source_plant.details,
        origin_history_id=source_plant.id
    )

    return {"message": "گیاه با موفقیت به باغچه شما اضافه شد.", "garden_id": new_garden_item.id}


@router.get("/list", response_model=List[GardenListResponse])
async def get_user_garden_list(
        request: Request,
        current_user: User = Depends(get_current_user)
):
    plants = await UserGarden.filter(
        user=current_user
    ).filter(
        Q(image_path__isnull=False) & ~Q(image_path="")
    ).order_by('-created_at').all()

    base_url = str(request.base_url).rstrip('/')
    results = []

    for plant in plants:

        # full image_path (thumbnail)
        full_main_url = None
        if plant.image_path:
            if plant.image_path.startswith("http"):
                full_main_url = plant.image_path
            else:
                clean_path = plant.image_path.lstrip("/")
                full_main_url = f"{base_url}/{clean_path}"

        # full image_paths (gallery)
        full_gallery = []
        if plant.image_paths:
            for p in plant.image_paths:
                if p.startswith("http"):
                    full_gallery.append(p)
                else:
                    clean_path = p.lstrip("/")
                    full_gallery.append(f"{base_url}/{clean_path}")

        display_nickname = plant.nickname if plant.nickname else plant.plant_name
        garden_item = await UserGarden.get_or_none(
            user=current_user,
            plant_name=plant.plant_name
        )

        in_garden = garden_item is not None
        garden_id = garden_item.id if garden_item else None
        results.append(GardenListResponse(
            id=plant.id,
            plant_name=plant.plant_name,
            nickname=display_nickname,
            image_path=full_main_url,
            image_paths=full_gallery,
            details=plant.details or {},
            in_garden=in_garden,
            garden_id=garden_id,
        ))

    return results


@router.delete("/{garden_id}")
async def delete_plant_from_garden(
        garden_id: int,
        current_user: User = Depends(get_current_user)
):
    deleted_count = await UserGarden.filter(id=garden_id, user=current_user).delete()
    if not deleted_count:
        raise HTTPException(status_code=404, detail="گیاه یافت نشد")
    return {"status": "deleted", "id": garden_id}


@router.delete("/history/{history_id}")
async def delete_garden_item_by_history(
        history_id: int,
        current_user: User = Depends(get_current_user)
):
    deleted_count = await UserGarden.filter(
        origin_history_id=history_id,
        user=current_user
    ).delete()

    if not deleted_count:
        raise HTTPException(status_code=404, detail="رکوردی برای حذف یافت نشد")

    return {"status": "deleted", "history_id": history_id}
