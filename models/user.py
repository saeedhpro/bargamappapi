from tortoise import fields, models


class User(models.Model):
    id = fields.IntField(pk=True)
    phone = fields.CharField(max_length=20, unique=True)

    # ✅ رابطه با جدول Role
    role = fields.ForeignKeyField(
        "models.Role",
        related_name="users",
        on_delete=fields.RESTRICT,  # نمی‌شود نقشی را پاک کرد که کاربر دارد
        null=True,
        default=1
    )

    created_at = fields.DatetimeField(auto_now_add=True)
    is_active = fields.BooleanField(default=True)

    class Meta:
        table = "user"

    def __str__(self):
        return f"{self.phone} ({self.role.name if self.role else 'No Role'})"

    async def can_see_all_conversations(self) -> bool:
        """
        آیا می‌تواند همه مکالمات را ببیند؟
        فقط admin, manager, support
        """
        await self.fetch_related("role")
        if not self.role:
            return False
        return self.role.name in ["admin", "manager", "support"]

    async def can_see_conversation(self, conversation) -> bool:
        """
        آیا می‌تواند این مکالمه را ببیند؟
        - admin/manager/support: همه چت‌ها
        - user: فقط چت‌های خودش
        """
        # اگر می‌تونه همه رو ببینه
        if await self.can_see_all_conversations():
            return True

        # فقط چت‌های خودش
        return conversation.user_id == self.id

    async def get_sender_type(self) -> str:
        """
        تعیین نوع فرستنده برای نمایش در UI
        """
        await self.fetch_related("role")

        if not self.role:
            return "user"

        # برگرداندن همان نام نقش
        return self.role.name

    def to_dict(self, include_role=False):
        data = {
            "id": self.id,
            "phone": self.phone,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

        if include_role and self.role:
            data["role"] = self.role.to_dict()

        return data