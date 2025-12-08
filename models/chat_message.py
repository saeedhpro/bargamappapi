from tortoise import fields, models


class ChatMessage(models.Model):
    id = fields.IntField(pk=True)

    conversation = fields.ForeignKeyField(
        "models.ChatConversation",
        related_name="messages",
        on_delete=fields.CASCADE
    )
    sender_user = fields.ForeignKeyField(
        "models.User",
        related_name="sent_messages",
        null=True,
        on_delete=fields.SET_NULL
    )
    sender = fields.CharField(max_length=20)  # user | support

    # پیام متنی (nullable برای پیام‌های فایل)
    text = fields.TextField(null=True)

    # پیام فایل / عکس
    file_url = fields.CharField(max_length=400, null=True)

    # text | photo | file
    message_type = fields.CharField(max_length=20, default="text")

    # وضعیت‌ها
    is_delivered = fields.BooleanField(default=False)
    is_seen = fields.BooleanField(default=False)

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "chat_messages"
