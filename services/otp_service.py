from hashlib import sha256

import random

from core.cache import redis_client

from core.config import settings


class OTPService:
    @staticmethod
    async def create_otp(phone: str):
        # otp = random.randint(10000, 99999)
        otp = 11111
        hashed = sha256(str(otp).encode()).hexdigest()
        await redis_client.set(f"otp:{phone}", hashed, ex=settings.OTP_EXPIRE_SECONDS)
        print("OTP for", phone, "=", otp)

        return True

    @staticmethod
    async def verify_otp(phone: str, code: str):
        hashed = await redis_client.get(f"otp:{phone}")
        if not hashed:
            return False
        incoming_hash = sha256(code.encode()).hexdigest()
        return incoming_hash == hashed
