from fastapi import APIRouter, HTTPException

from models.user import User
from schemas.auth import SendOtpRequest, VerifyOtpRequest
from schemas.user import UserOut
from services.otp_service import OTPService
from services.subscription import SubscriptionService
from services.user_service import UserService
from core.security import create_access_token

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


@router.post("/send-otp")
async def send_otp(data: SendOtpRequest):
    await OTPService.create_otp(data.phone)
    return {"message": "OTP sent"}


@router.post("/verify-otp")
async def verify_otp(data: VerifyOtpRequest):
    ok = await OTPService.verify_otp(data.phone, data.code)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    user = await UserService.get_or_none_user(data.phone)
    if not user:
        user = await User.create(phone=data.phone)
        await SubscriptionService.assign_default_plan(user.id)

    token = create_access_token(user.id)

    sub_info = await SubscriptionService.get_user_active_subscription_info(user.id)

    user_out = UserOut.from_orm(user)
    user_out.subscription = sub_info

    return {
        "access_token": token,
        "refresh_token": "",
        "token_type": "bearer",
        "user": user_out
    }
