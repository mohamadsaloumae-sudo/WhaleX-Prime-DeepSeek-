"""WebSocket Manager - WhaleX Prime"""
import asyncio
import json
import logging
import time
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect
from app.core.redis_manager import redis_mgr
from app.auth.jwt import decode_access_token

log = logging.getLogger("whalex.ws")

# Active connections
class ConnectionManager:
    def __init__(self):
        self._connections: Dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()
    
    async def add(self, client_id: str, websocket: WebSocket):
        async with self._lock:
            self._connections[client_id] = websocket
        log.info(f"WS connected: {client_id} — total: {len(self._connections)}")
    
    async def remove(self, client_id: str):
        async with self._lock:
            self._connections.pop(client_id, None)
        log.info(f"WS disconnected: {client_id} — total: {len(self._connections)}")
    
    async def broadcast(self, data: dict):
        """Broadcast to all connected clients"""
        if not self._connections:
            return
        
        msg = json.dumps(data, ensure_ascii=False)
        dead = []
        
        async with self._lock:
            clients = list(self._connections.items())
        
        async def send_one(client_id: str, ws: WebSocket):
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(client_id)
        
        await asyncio.gather(*[send_one(cid, ws) for cid, ws in clients], return_exceptions=True)
        
        # Clean dead connections
        if dead:
            async with self._lock:
                for cid in dead:
                    self._connections.pop(cid, None)
            log.debug(f"Cleaned {len(dead)} dead connections")
    
    @property
    def count(self) -> int:
        return len(self._connections)


manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint with authentication"""
    
    # Accept connection
    await websocket.accept()
    
    # Get token from query parameter
    token = websocket.query_params.get("token")
    client_id = None
    
    # Verify token
    if token:
        payload = decode_access_token(token)
        if payload:
            client_id = payload.get("sub")
    
    if not client_id:
        client_id = f"anon_{int(time.time() * 1000)}_{id(websocket)}"
    
    await manager.add(client_id, websocket)
    
    # Send initial ping
    await websocket.send_text(json.dumps({"event": "ping", "ts": int(time.time())}))
    
    try:
        # Keep connection alive
        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                if msg:
                    await handle_client_message(client_id, websocket, msg)
            except asyncio.TimeoutError:
                # Send ping to keep alive
                await websocket.send_text(json.dumps({"event": "ping", "ts": int(time.time())}))
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        log.debug(f"WS error for {client_id}: {e}")
    finally:
        await manager.remove(client_id)


async def handle_client_message(client_id: str, websocket: WebSocket, msg: str):
    """Handle incoming WebSocket messages"""
    try:
        data = json.loads(msg)
        event = data.get("event", "")
        
        if event == "pong":
            pass  # Connection alive
        
        elif event == "subscribe":
            symbol = data.get("symbol", "")
            if symbol:
                log.debug(f"WS {client_id} subscribed to {symbol}")
                await websocket.send_text(json.dumps({
                    "event": "subscribed",
                    "symbol": symbol
                }))
        
        elif event == "ping":
            await websocket.send_text(json.dumps({"event": "pong", "ts": int(time.time())}))
    
    except Exception as e:
        log.debug(f"Message handling error: {e}")


async def start_ws_relay():
    """Start Redis to WebSocket relay"""
    log.info("WebSocket Relay started — forwarding from Redis to clients")
    
    async for data in redis_mgr.subscribe([redis_mgr.PRICES_CHANNEL, redis_mgr.SIGNALS_CHANNEL]):
        try:
            if manager.count > 0:
                await manager.broadcast(data)
        except Exception as e:
            log.error(f"Relay error: {e}")