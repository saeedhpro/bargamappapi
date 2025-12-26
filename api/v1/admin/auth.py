from fastapi import APIRouter, HTTPException
from models.user import User
from services.otp_service import OTPService
from core.security import create_access_token
from schemas.auth import SendOtpRequest, VerifyOtpRequest

router = APIRouter(
    prefix="/api/v1/admin/auth",
    tags=["AdminAuth"]
)

ALLOWED_ROLES = ["admin", "support"]


@router.post("/send-otp")
async def send_admin_otp(data: SendOtpRequest):
    await OTPService.create_otp(data.phone)
    return {"message": "OTP sent"}


@router.post("/verify-otp")
async def verify_admin_otp(data: VerifyOtpRequest):
    ok = await OTPService.verify_otp(data.phone, data.code)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    user = await User.get_or_none(phone=data.phone).prefetch_related("role")
    if not user or not user.role:
        raise HTTPException(status_code=403, detail="Access denied")

    if user.role.name not in ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Not an admin")

    token = create_access_token(user.id)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "phone": user.phone,
            "role": user.role.name
        }
    }
