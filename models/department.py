from tortoise import fields, models


class Department(models.Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100, unique=True)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "departments"
        ordering = ["id"]

    def __str__(self):
        return self.name
