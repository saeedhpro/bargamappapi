from tortoise import fields, models
from models.chat_message import ChatMessage


class ChatConversation(models.Model):
    id = fields.IntField(pk=True)
    title = fields.CharField(max_length=255)
    created_at = fields.DatetimeField(auto_now_add=True)
    last_activity = fields.DatetimeField(auto_now=True)
    messages: fields.ReverseRelation["ChatMessage"]

    user = fields.ForeignKeyField(
        "models.User",
        related_name="conversations",
        on_delete=fields.CASCADE,
        description="کاربری که این مکالمه را ایجاد کرده"
    )

    department = fields.ForeignKeyField(
        "models.Department",
        related_name="conversations",
        on_delete=fields.RESTRICT,
        description="دپارتمان پشتیبانی"
    )

    class Meta:
        table = "chat_conversations"
        ordering = ["-last_activity"]

    def __str__(self):
        return f"Conversation #{self.id}: {self.title}"
