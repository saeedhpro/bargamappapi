from tortoise import models, fields


class User(models.Model):
    id = fields.IntField(pk=True)
    phone = fields.CharField(max_length=20, unique=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    is_active = fields.BooleanField(default=True)

    def str(self):
        return self.phone
