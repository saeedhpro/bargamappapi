from fastapi import APIRouter, WebSocket, Depends, Query
from starlette import status
from starlette.websockets import WebSocketDisconnect

from core.logger import ws_logger
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
    ws_logger.log_connect(user_id, conversation_id)

    current_user = await User.get_or_none(id=user_id).prefetch_related("role")
    if not current_user:
        ws_logger.logger.error(f"User {user_id} not found")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await ws_manager.add(conversation_id, websocket)
    ws_logger.logger.info(f"✅ User {current_user.id} joined conversation {conversation_id}")

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            # ✅ لاگ کامل داده دریافتی
            ws_logger.log_message(action, {
                "conversation_id": conversation_id,
                "user_id": current_user.id,
                "data": data
            })

            if action == "send_message":
                try:
                    ws_logger.logger.debug(
                        f"📤 Attempting to send message: "
                        f"conv={conversation_id}, user={current_user.id}, "
                        f"text_len={len(data.get('text', ''))}, type={data.get('type', 'text')}"
                    )

                    msg = await service.send_message(
                        conversation_id=conversation_id,
                        sender_user=current_user,
                        sender_type=current_user.role.name,
                        text=data.get("text"),
                        file_url=data.get("file_url"),
                        message_type=data.get("type", "text"),
                    )

                    ws_logger.logger.info(f"✅ Message sent successfully: id={msg['id']}")
                    ws_logger.log_broadcast(conversation_id, "message")

                    await ws_manager.broadcast(conversation_id, {
                        "type": "message",
                        "message": msg
                    })

                except Exception as e:
                    ws_logger.log_error("send_message", e)
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Failed to send message: {str(e)}"
                    })

            elif action == "typing":
                ws_logger.logger.debug(
                    f"⌨️ Typing indicator: conv={conversation_id}, "
                    f"user={current_user.id}, is_typing={data.get('is_typing')}"
                )

                await ws_manager.broadcast(conversation_id, {
                    "type": "typing",
                    "from": "user",
                    "is_typing": data.get("is_typing", False)
                })

            elif action == "seen":
                last_id = data.get("last_message_id")

                try:
                    ws_logger.logger.debug(
                        f"👁️ Marking messages as seen: conv={conversation_id}, last_id={last_id}"
                    )

                    await service.mark_seen(conversation_id, last_id)

                    ws_logger.log_broadcast(conversation_id, "seen")

                    await ws_manager.broadcast(conversation_id, {
                        "type": "seen",
                        "last_id": last_id
                    })

                except Exception as e:
                    ws_logger.log_error("mark_seen", e)

    except WebSocketDisconnect:
        ws_logger.log_disconnect(user_id, conversation_id)
    except Exception as e:
        ws_logger.log_error("websocket_loop", e)
    finally:
        await ws_manager.remove(conversation_id, websocket)
        ws_logger.logger.info(f"🧹 Cleaned up connection: user={user_id}, conv={conversation_id}")
