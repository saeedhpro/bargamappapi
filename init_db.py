from tortoise import Tortoise

# 1. تعریف تنظیمات در یک دیکشنری به نام TORTOISE_ORM
TORTOISE_ORM = {
    "connections": {
        "default": "postgres://saeed:saeed%402311@localhost:5432/golbeendb"
    },
    "apps": {
        "models": {
            "models": [
                "models.user",
                "models.subscription",
                "models.history",
                "models.garden",
                "aerich.models"
            ],
            "default_connection": "default",
        }
    },
}

async def init_db():
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas()


async def init_db_data():
    pass
