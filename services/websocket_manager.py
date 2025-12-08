from fastapi import WebSocket


class WebSocketManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WebSocketManager, cls).__new__(cls)
            cls._instance.active_connections = {}
        return cls._instance

    # ---------------------------------------------
    # افزودن اتصال جدید
    # ---------------------------------------------
    async def add(self, conversation_id: int, websocket: WebSocket):
        """افزودن اتصال جدید"""
        if conversation_id not in self.active_connections:
            self.active_connections[conversation_id] = []
        self.active_connections[conversation_id].append(websocket)
        print(f"✅ WebSocket connected to conversation {conversation_id}")

    # ---------------------------------------------
    # حذف اتصال هنگام قطع
    # ---------------------------------------------
    async def remove(self, conversation_id: int, websocket: WebSocket):
        """حذف اتصال"""
        if conversation_id in self.active_connections:
            if websocket in self.active_connections[conversation_id]:
                self.active_connections[conversation_id].remove(websocket)

                if not self.active_connections[conversation_id]:
                    del self.active_connections[conversation_id]

        print(f"❌ WebSocket disconnected from conversation {conversation_id}")

    # ---------------------------------------------
    # ارسال پیام به همه کاربران مکالمه
    # ---------------------------------------------
    async def broadcast(self, conversation_id: int, data: dict):
        """ارسال پیام به همه کاربران مکالمه"""
        if conversation_id not in self.active_connections:
            return

        dead_connections = []

        for ws in list(self.active_connections[conversation_id]):
            try:
                await ws.send_json(data)
            except Exception as e:
                print(f"⚠️ Failed to send to WebSocket: {e}")
                dead_connections.append(ws)

        # حذف کانکشن‌های خراب
        for ws in dead_connections:
            await self.remove(conversation_id, ws)