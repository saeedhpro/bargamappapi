from models.user import User


class UserService:
    @staticmethod
    async def get_or_create_user(phone: str):
        user, created = await User.get_or_create(phone=phone)
        return user

    @staticmethod
    async def get_or_none_user(phone: str):
        user = await User.get_or_none(phone=phone)
        return user
