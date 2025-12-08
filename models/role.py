from tortoise import fields, models


class Role(models.Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=50, unique=True)
    display_name = fields.CharField(max_length=100)
    created_at = fields.DatetimeField(auto_now_add=True)
    is_active = fields.BooleanField(default=True)

    class Meta:
        table = "roles"

    def __str__(self):
        return self.display_name
