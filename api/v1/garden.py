from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, Depends, Request

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
    source_plant = await PlantHistory.get_or_none(id=req.history_id)

    if not source_plant:
        raise HTTPException(status_code=404, detail="گیاه مورد نظر یافت نشد")

    new_garden_item = await UserGarden.create(
        user=current_user,
        plant_name=source_plant.plant_name,
        nickname=req.nickname or source_plant.common_name,
        image_path=source_plant.image_path,
        details=source_plant.details,
        origin_history_id=source_plant.id
    )

    return {"message": "به باغچه اضافه شد", "garden_id": new_garden_item.id}


@router.get("/list", response_model=List[GardenListResponse])
async def get_user_garden_list(
        request: Request,
        current_user: User = Depends(get_current_user)
):
    plants = await UserGarden.filter(user=current_user).order_by('-created_at').all()

    base_url = str(request.base_url).rstrip('/')
    results = []

    for plant in plants:
        full_image_url = None
        if plant.image_path:
            if not plant.image_path.startswith('http'):
                clean_path = plant.image_path.lstrip('/')
                full_image_url = f"{base_url}/{clean_path}"
            else:
                full_image_url = plant.image_path

        display_nickname = plant.nickname if plant.nickname else plant.plant_name

        results.append(GardenListResponse(
            id=plant.id,
            plant_name=plant.plant_name,
            nickname=display_nickname,
            image_url=full_image_url,
            details=plant.details if plant.details else {}
        ))

    return results


@router.delete("/{plant_id}")
async def delete_plant_from_garden(
    plant_id: int,
    current_user: User = Depends(get_current_user)
):
    deleted_count = await UserGarden.filter(id=plant_id, user=current_user).delete()
    if not deleted_count:
        raise HTTPException(status_code=404, detail="گیاه یافت نشد")
    return {"status": "deleted", "id": plant_id}