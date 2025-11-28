from pydantic import BaseModel, Field


class SendOtpRequest(BaseModel):
    phone: str = Field(..., alias="phone_number")


class VerifyOtpRequest(BaseModel):
    phone: str = Field(..., alias="phone_number")
    code: str
