from typing import Dict, Any, Optional
import os
import json
import asyncio
import logging

logger = logging.getLogger(__name__)


class SocketService:
    """Socket.io service for real-time updates"""
    
    def __init__(self):
        self._connections: Dict[str, set] = {}
        self._server = None
    
    def set_server(self, server):
        """Set the Socket.io server instance"""
        self._server = server
    
    async def connect(self, session_id: str, user_id: Optional[str] = None):
        """Handle new connection"""
        if user_id:
            if user_id not in self._connections:
                self._connections[user_id] = set()
            self._connections[user_id].add(session_id)
        logger.info(f"Client connected: {session_id}, user: {user_id}")
    
    async def disconnect(self, session_id: str, user_id: Optional[str] = None):
        """Handle disconnection"""
        if user_id and user_id in self._connections:
            self._connections[user_id].discard(session_id)
            if not self._connections[user_id]:
                del self._connections[user_id]
        logger.info(f"Client disconnected: {session_id}")
    
    async def broadcast(self, event_type: str, data: Dict[str, Any], user_id: Optional[str] = None):
        """Broadcast event to connected clients"""
        if not self._server:
            logger.warning("Socket.io server not initialized")
            return
        
        payload = json.dumps({
            "type": event_type,
            "data": data,
        })
        
        if user_id and user_id in self._connections:
            for session_id in self._connections[user_id]:
                await self._server.emit(event_type, payload, room=session_id)
        else:
            await self._server.emit(event_type, payload, broadcast=True)
        
        logger.info(f"Broadcast: {event_type}")
    
    async def emit_to_user(self, user_id: str, event_type: str, data: Dict[str, Any]):
        """Emit event to specific user"""
        await self.broadcast(event_type, data, user_id)


socket_service = SocketService()
