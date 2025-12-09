from fastapi import APIRouter, WebSocket, Depends, Query
from starlette import status
from starlette.websockets import WebSocketDisconnect

from models.user import User
from services.chat_service import ChatService
from services.websocket_manager import WebSocketManager

router = APIRouter(prefix="/api/v1/ws", tags=["Chat"])

ws_manager = WebSocketManager()


@router.websocket("/chat/{conversation_id}")
async def chat_ws(
    websocket: WebSocket,
    conversation_id: int,
    user_id: int = Query(...),
    service: ChatService = Depends(),
):
    await websocket.accept()
    print(f"🔗 WebSocket connection accepted for user_id={user_id}, conversation={conversation_id}")

    current_user = await User.get_or_none(id=user_id).prefetch_related("role")
    if not current_user:
        print(f"❌ User {user_id} not found")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await ws_manager.add(conversation_id, websocket)
    print(f"✅ User {current_user.id} joined conversation {conversation_id}")

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            print(f"📩 Received action: {action} from user {current_user.id}")

            if action == "send_message":
                msg = await service.send_message(
                    conversation_id=conversation_id,
                    sender_user=current_user,
                    sender_type=current_user.role.name,
                    text=data.get("text"),
                    file_url=data.get("file_url"),
                    message_type=data.get("type", "text"),
                )

                await ws_manager.broadcast(conversation_id, {
                    "type": "message",
                    "message": msg
                })

            elif action == "typing":
                await ws_manager.broadcast(conversation_id, {
                    "type": "typing",
                    "from": "user",
                    "is_typing": data.get("is_typing", False)
                })

            elif action == "seen":
                last_id = data.get("last_message_id")
                await service.mark_seen(conversation_id, last_id)

                await ws_manager.broadcast(conversation_id, {
                    "type": "seen",
                    "last_id": last_id
                })

    except WebSocketDisconnect:
        print(f"🔌 WebSocket disconnected from conversation {conversation_id}")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
    finally:
        await ws_manager.remove(conversation_id, websocket)
