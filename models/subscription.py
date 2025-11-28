from tortoise import fields, models
from enum import Enum


class ToolType(str, Enum):
    PLANT_ID = "plant_id"
    DISEASE_ID = "disease_id"


class SubscriptionPlan(models.Model):
    id = fields.IntField(pk=True)
    title = fields.CharField(max_length=100)
    description = fields.TextField(null=True)
    price = fields.IntField(default=0)
    duration_days = fields.IntField(null=True)

    daily_plant_id_limit = fields.IntField(default=1)
    daily_disease_id_limit = fields.IntField(default=1)

    is_default = fields.BooleanField(default=False)
    is_active = fields.BooleanField(default=True)

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "subscription_plans"


class UserSubscription(models.Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="subscriptions")
    plan = fields.ForeignKeyField("models.SubscriptionPlan", related_name="user_subs", null=True)

    frozen_daily_plant_id_limit = fields.IntField()
    frozen_daily_disease_id_limit = fields.IntField()

    start_date = fields.DatetimeField(auto_now_add=True)
    end_date = fields.DatetimeField(null=True)

    is_active = fields.BooleanField(default=True)

    class Meta:
        table = "user_subscriptions"


class UsageLog(models.Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="usage_logs")
    tool_type = fields.CharEnumField(ToolType)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "usage_logs"
