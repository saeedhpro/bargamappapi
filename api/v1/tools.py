from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status

from models.history import PlantHistory
from services.subscription import SubscriptionService
from services.plant_identifier import PlantIdentifierService
from models.subscription import ToolType
from api.deps import get_current_user
from models.user import User

router = APIRouter(prefix="/api/v1/tools", tags=["Tools"])


@router.post("/identify-plant")
async def identify_plant(
        file: UploadFile = File(..., alias="images"),
        current_user: User = Depends(get_current_user),
):
    await SubscriptionService.check_and_record_usage(
        user_id=current_user.id,
        tool_type=ToolType.PLANT_ID
    )

    try:
        result = await PlantIdentifierService.identify_and_analyze(file)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")

    try:
        if result['status'] == 'success':
            await PlantHistory.create(
                user=current_user,
                plant_name=result['plant_name'],
                common_name=result['common_name'],
                accuracy=result['accuracy'],
                description=result['description'],
                image_url=result['image_url']
            )
    except Exception as e:
        print(f"Failed to save history: {e}")
    return result


@router.post("/identify-disease")
async def identify_disease(
        file: UploadFile = File(..., alias="images"),
        current_user: User = Depends(get_current_user)
):
    await SubscriptionService.check_and_record_usage(
        user_id=current_user.id,
        tool_type=ToolType.DISEASE_ID
    )
    return {"message": "Processing started...", "disease": "Not Implemented Yet"}
