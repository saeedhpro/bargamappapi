from fastapi import APIRouter, HTTPException, Depends

from api.deps import get_current_user
from models.garden import UserGarden
from models.history import PlantHistory
from models.user import User
from schemas.garden import AddFromHistoryRequest

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