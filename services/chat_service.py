from models.chat_conversation import ChatConversation
from models.chat_message import ChatMessage
from tortoise.expressions import Q
from models.user import User
from datetime import datetime


class ChatService:

    # --------------------------------------
    # ایجاد مکالمه جدید
    # --------------------------------------
    async def create_conversation(self, title: str, user: User):
        conv = await ChatConversation.create(title=title, user=user)
        # ✅ حتماً user رو fetch کن
        await conv.fetch_related("user", "user__role")
        return await self.serialize_conversation(conv)

    # --------------------------------------
    # دریافت لیست مکالمات + آخرین پیام
    # --------------------------------------
    async def get_conversations(self, page: int, search: str, user: User | None):
        size = 20
        offset = (page - 1) * size

        # فیلتر بر اساس user
        filters = Q()

        if search:
            filters &= Q(title__icontains=search)

        if user:
            filters &= Q(user_id=user.id)

        # ✅ حتماً از prefetch_related استفاده کن
        conversations = await (
            ChatConversation.filter(filters)
            .order_by("-last_activity")
            .offset(offset)
            .limit(size)
            .prefetch_related("user", "user__role")
        )

        result = []
        for conv in conversations:
            result.append(await self.serialize_conversation(conv))

        return result

    # --------------------------------------
    # دریافت پیام‌های یک مکالمه
    # --------------------------------------
    async def get_messages(self, conversation_id: int):
        msgs = await ChatMessage.filter(
            conversation_id=conversation_id
        ).order_by("id").prefetch_related("sender_user", "sender_user__role")

        return [await self.serialize_message(msg) for msg in msgs]

    # --------------------------------------
    # ارسال پیام جدید
    # --------------------------------------
    async def send_message(
            self,
            conversation_id: int,
            sender_user: User = None,
            sender_type: str = "user",
            text: str = None,
            file_url: str = None,
            message_type: str = "text"
    ):
        msg = await ChatMessage.create(
            conversation_id=conversation_id,
            sender_user=sender_user,
            sender_type=sender_type,
            text=text,
            file_url=file_url,
            message_type=message_type,
            is_delivered=True
        )

        # ✅ آپدیت last_activity
        await ChatConversation.filter(id=conversation_id).update(
            last_activity=datetime.now()
        )

        # ✅ fetch کردن sender_user قبل از serialize
        if sender_user:
            await msg.fetch_related("sender_user", "sender_user__role")

        return await self.serialize_message(msg)

    # --------------------------------------
    # علامت‌گذاری به عنوان خوانده‌شده
    # --------------------------------------
    async def mark_seen(self, conversation_id: int, last_message_id: int):
        await ChatMessage.filter(
            conversation_id=conversation_id,
            id__lte=last_message_id
        ).update(is_seen=True)

    # --------------------------------------
    # Serialize کردن مکالمه
    # --------------------------------------
    async def serialize_conversation(self, conv: ChatConversation):
        """تبدیل مکالمه به دیکشنری - با جلوگیری از QuerySet"""

        # ✅ دریافت آخرین پیام
        last_msg = await ChatMessage.filter(
            conversation_id=conv.id
        ).order_by("-id").prefetch_related("sender_user", "sender_user__role").first()

        # ✅ تبدیل user به دیکشنری خالص
        user_data = None
        if conv.user_id:
            # بررسی اینکه آیا user fetch شده یا نه
            try:
                # ✅ اگر fetch نشده، الان fetch میکنیم
                if not hasattr(conv, '_prefetched_objects') or 'user' not in conv._prefetched_objects:
                    await conv.fetch_related("user", "user__role")

                # ✅ حالا user رو به dict تبدیل میکنیم
                if conv.user:
                    user_data = {
                        "id": conv.user.id,
                        "phone": conv.user.phone,
                        "full_name": getattr(conv.user, "full_name", None),
                        "role": conv.user.role.name if hasattr(conv.user, "role") and conv.user.role else "user"
                    }
            except Exception as e:
                print(f"⚠️ خطا در serialize کردن user: {e}")
                user_data = None

        return {
            "id": conv.id,
            "title": conv.title,
            "created_at": conv.created_at.isoformat(),
            "last_activity": conv.last_activity.isoformat() if hasattr(conv,
                                                                       "last_activity") and conv.last_activity else None,
            "last_message": await self.serialize_message(last_msg) if last_msg else None,
            "user": user_data  # ✅ فقط dict ساده
        }

    # --------------------------------------
    # Serialize کردن پیام
    # --------------------------------------
    async def serialize_message(self, msg: ChatMessage):
        """تبدیل پیام به دیکشنری - با جلوگیری از QuerySet"""
        if not msg:
            return None

        # ✅ تبدیل sender_user به dict
        sender_data = None
        if hasattr(msg, "sender_user_id") and msg.sender_user_id:
            try:
                if not hasattr(msg, '_prefetched_objects') or 'sender_user' not in msg._prefetched_objects:
                    await msg.fetch_related("sender_user", "sender_user__role")

                if msg.sender_user:
                    sender_data = {
                        "id": msg.sender_user.id,
                        "phone": msg.sender_user.phone,
                        "full_name": getattr(msg.sender_user, "full_name", None),
                    }
            except Exception as e:
                print(f"⚠️ خطا در serialize کردن sender: {e}")

        return {
            "id": msg.id,
            "conversation_id": msg.conversation_id,
            "sender_user": sender_data,  # ✅ dict خالص
            "sender_type": msg.sender_type if hasattr(msg, "sender_type") else "user",
            "text": msg.text,
            "file_url": msg.file_url,
            "message_type": msg.message_type,
            "is_delivered": msg.is_delivered,
            "is_seen": msg.is_seen,
            "created_at": msg.created_at.isoformat()
        }
