from tortoise import fields, models


class PlantHistory(models.Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField('models.User', related_name='plant_history')

    # مسیر عکس ذخیره شده روی سرور
    image_path = fields.CharField(max_length=500, null=True)

    plant_name = fields.CharField(max_length=255)  # نام علمی
    common_name = fields.CharField(max_length=255, null=True)  # نام فارسی
    accuracy = fields.FloatField()

    # توضیحات کلی متنی
    description = fields.TextField(null=True)

    # ذخیره کل آبجکت جیسون (نور، دما، آبیاری و...) برای نمایش مجدد در UI
    details = fields.JSONField(null=True)

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "plant_histories"
