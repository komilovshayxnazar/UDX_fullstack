from fastapi import WebSocket

class ChatRoomManager:
    def __init__(self):
        # chat_id -> list of WebSockets
        self.rooms: dict[str, list[WebSocket]] = {}

    async def connect(self, chat_id: str, websocket: WebSocket):
        await websocket.accept()
        if chat_id not in self.rooms:
            self.rooms[chat_id] = []
        self.rooms[chat_id].append(websocket)

    def disconnect(self, chat_id: str, websocket: WebSocket):
        if chat_id in self.rooms:
            if websocket in self.rooms[chat_id]:
                self.rooms[chat_id].remove(websocket)
            if not self.rooms[chat_id]:
                self.rooms.pop(chat_id, None)

    async def broadcast(self, chat_id: str, message: str, sender_websocket: WebSocket):
        if chat_id in self.rooms:
            for connection in self.rooms[chat_id]:
                await connection.send_text(message)

chat_manager = ChatRoomManager()
