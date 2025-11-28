from tortoise import fields, models


class PlantHistory(models.Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField('models.User', related_name='plant_history')
    image_url = fields.CharField(max_length=500, null=True)
    plant_name = fields.CharField(max_length=255)
    common_name = fields.CharField(max_length=255, null=True)
    accuracy = fields.FloatField()
    description = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "plant_histories"
