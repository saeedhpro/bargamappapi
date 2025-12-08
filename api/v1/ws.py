from fastapi import APIRouter, WebSocket, Depends, Query
from starlette.websockets import WebSocketDisconnect

from api.deps import get_current_user
from models.user import User
from services.chat_service import ChatService
from services.websocket_manager import WebSocketManager

router = APIRouter(prefix="/api/v1/ws", tags=["Chat"])

ws_manager = WebSocketManager()


@router.websocket("/chat/{conversation_id}")
async def chat_ws(
    websocket: WebSocket,
    conversation_id: int,
    service: ChatService = Depends(),
    token: str = Query(...)
):
    try:
        current_user = await get_current_user_from_token(token)
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    """WebSocket برای چت لحظه‌ای"""
    await websocket.accept()
    await ws_manager.add(conversation_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            print(f"📩 Received action: {action} for conversation {conversation_id}")

            # ارسال پیام
            if action == "send_message":
                message_type = data.get("type", "text")

                msg = await service.send_message(
                    conversation_id=conversation_id,
                    sender_type=data.get("sender", "user"),
                    sender_user=current_user,
                    text=data.get("text"),
                    file_url=data.get("file_url"),
                    message_type=message_type
                )

                await ws_manager.broadcast(conversation_id, {
                    "type": "message",
                    "message": msg
                })

            # تایپ کردن
            elif action == "typing":
                await ws_manager.broadcast(conversation_id, {
                    "type": "typing",
                    "from": data.get("from", "user"),
                    "is_typing": data.get("is_typing", False)
                })

            # خوانده‌شدن پیام‌ها
            elif action == "seen":
                last_id = data.get("last_message_id")
                await service.mark_seen(conversation_id, last_id)

                await ws_manager.broadcast(conversation_id, {
                    "type": "seen",
                    "last_id": last_id
                })

    except WebSocketDisconnect:
        print(f"🔌 WebSocket disconnected: conversation {conversation_id}")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
    finally:
        await ws_manager.remove(conversation_id, websocket)