import os
from uuid import uuid4

from fastapi import APIRouter, Depends, UploadFile, Request

from api.deps import get_current_user
from models.user import User
from services.chat_service import ChatService

router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])


# ----------------------------------------
# 1. ایجاد مکالمه جدید
# ----------------------------------------
@router.post("/conversations")
async def start_conversation(
    payload: dict,
    service: ChatService = Depends(),
    current_user: User = Depends(get_current_user)
):
    """ایجاد مکالمه جدید"""
    title = payload.get("title", "مکالمه جدید")
    conv = await service.create_conversation(title, user=current_user)
    return {"conversation": conv}



# ----------------------------------------
# 2. دریافت لیست مکالمات
# ----------------------------------------
@router.get("/conversations")
async def list_conversations(
    page: int = 1,
    search: str = "",
    service: ChatService = Depends(),
    current_user: User = Depends(get_current_user)
):
    await current_user.fetch_related("role")
    if current_user.role and (current_user.role.name == "admin" or current_user.role.name == "support"):
        """دریافت لیست مکالمات"""
        convs = await service.get_conversations(page, search, None)
        return {"conversations": convs}
    else:
        """دریافت لیست مکالمات"""
        convs = await service.get_conversations(page, search, current_user)
        return {"conversations": convs}

# ----------------------------------------
# 3. دریافت پیام‌های یک مکالمه
# ----------------------------------------
@router.get("/messages/{conversation_id}")
async def conversation_messages(
    conversation_id: int,
    service: ChatService = Depends()
):
    """دریافت پیام‌های یک مکالمه"""
    msgs = await service.get_messages(conversation_id)
    return {"messages": msgs}


@router.post("/upload")
async def upload_file(request: Request, file: UploadFile):
    """آپلود فایل"""
    ext = file.filename.split(".")[-1]
    unique = f"{uuid4()}.{ext}"

    save_path = f"static/chat/{unique}"
    os.makedirs("static/chat", exist_ok=True)

    with open(save_path, "wb") as f:
        f.write(await file.read())

    path = f"/static/chat/{unique}"
    base_url = str(request.base_url).rstrip('/')
    clean_path = path.lstrip("/")
    full_url = f"{base_url}/{clean_path}"

    return {"url": full_url}