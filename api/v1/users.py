from fastapi import APIRouter, Depends
from schemas.user import UserOut
from models.user import User
from api.deps import get_current_user
from services.subscription import SubscriptionService

router = APIRouter(prefix="/api/v1/users", tags=["Users"])


@router.get("/me", response_model=UserOut)
async def read_users_me(current_user: User = Depends(get_current_user)):
    sub_info = await SubscriptionService.get_user_active_subscription_info(current_user.id)

    user_out = UserOut.from_orm(current_user)

    user_out.subscription = sub_info

    return user_out
