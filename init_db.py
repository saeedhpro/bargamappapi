from tortoise import Tortoise

from models.subscription import SubscriptionPlan


async def init_db():
    await Tortoise.init(
        db_url="postgres://saeed:saeed%402311@localhost:5432/golbeendb",
        modules={"models": ["models.user", "models.subscription"]}
    )
    await Tortoise.generate_schemas()


async def init_db_data():
    pass
    # default_exists = await SubscriptionPlan.filter(is_default=True).exists()
    # if not default_exists:
    #     await SubscriptionPlan.create(
    #         title="اشتراک رایگان",
    #         description="شامل استفاده محدود روزانه",
    #         price=0,
    #         daily_plant_id_limit=1,
    #         daily_disease_id_limit=1,
    #         is_default=True,
    #         is_active=True
    #     )
    #     print("Default free plan created.")
