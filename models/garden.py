from tortoise import fields, models


class UserGarden(models.Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField('models.User', related_name='garden_plants')

    plant_name = fields.CharField(max_length=255)
    nickname = fields.CharField(max_length=255, null=True)
    image_path = fields.CharField(max_length=500)
    details = fields.JSONField(default={})

    origin_history_id = fields.IntField(null=True)

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "user_garden"
