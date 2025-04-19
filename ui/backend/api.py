"""
FastAPI backend for Sarvagya.
Provides REST API and WebSocket endpoints for interacting with the agent system.
"""
import asyncio
from typing import Dict, List, Optional, Any
import uuid
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis.asyncio as redis

from core.orchestrator import get_orchestrator, Orchestrator


# API models
class TaskRequest(BaseModel):
    """Request to create a new task."""
    task_description: str


class TaskResponse(BaseModel):
    """Response containing task information."""
    task_id: str
    status: str


class TaskStatusResponse(BaseModel):
    """Response containing task status."""
    task_id: str
    status: str
    current_step: Optional[str] = None
    progress: str
    error: Optional[str] = None


class TaskResultResponse(BaseModel):
    """Response containing complete task result."""
    task_id: str
    task_description: str
    status: str
    messages: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    error: Optional[str] = None


# Create FastAPI app
app = FastAPI(
    title="Sarvagya API",
    description="API for interacting with the Sarvagya agent system",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub_task = None
    
    async def connect(self, websocket: WebSocket, task_id: str):
        await websocket.accept()
        if task_id not in self.active_connections:
            self.active_connections[task_id] = []
        self.active_connections[task_id].append(websocket)
        
        # Initialize Redis PubSub if not already done
        if self.redis_client is None:
            self.redis_client = redis.Redis.from_url("redis://localhost:6379/0")
            # Start listening for updates in the background
            self.pubsub_task = asyncio.create_task(self._listen_for_updates())
    
    def disconnect(self, websocket: WebSocket, task_id: str):
        if task_id in self.active_connections:
            if websocket in self.active_connections[task_id]:
                self.active_connections[task_id].remove(websocket)
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]
    
    async def send_update(self, task_id: str, message: str):
        if task_id in self.active_connections:
            for connection in self.active_connections[task_id]:
                await connection.send_text(message)
    
    async def broadcast(self, message: str):
        for connections in self.active_connections.values():
            for connection in connections:
                await connection.send_text(message)
    
    async def _listen_for_updates(self):
        """Listen for updates from Redis PubSub and forward to WebSocket clients."""
        pubsub = self.redis_client.pubsub()
        
        # Subscribe to all task updates
        await pubsub.psubscribe("sarvagya:updates:*")
        
        # Also subscribe to global updates
        await pubsub.subscribe("sarvagya:updates")
        
        try:
            async for message in pubsub.listen():
                if message["type"] in ["pmessage", "message"]:
                    # Extract task_id from channel
                    channel = message["channel"].decode("utf-8")
                    if channel == "sarvagya:updates":
                        # Global update, broadcast to all
                        await self.broadcast(message["data"].decode("utf-8"))
                    else:
                        # Task-specific update
                        task_id = channel.split(":")[-1]
                        await self.send_update(task_id, message["data"].decode("utf-8"))
        except Exception as e:
            print(f"Error in PubSub listener: {e}")
        finally:
            await pubsub.unsubscribe()
            await pubsub.punsubscribe()


# Create connection manager
manager = ConnectionManager()


# Dependency to get orchestrator
def get_orchestrator_dep() -> Orchestrator:
    return get_orchestrator()


@app.post("/tasks", response_model=TaskResponse)
async def create_task(
    request: TaskRequest,
    background_tasks: BackgroundTasks,
    orchestrator: Orchestrator = Depends(get_orchestrator_dep)
):
    """Create a new task."""
    task_id = await orchestrator.submit_task(request.task_description)
    return {"task_id": task_id, "status": "submitted"}


@app.get("/tasks/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    orchestrator: Orchestrator = Depends(get_orchestrator_dep)
):
    """Get the status of a task."""
    status = await orchestrator.get_task_status(task_id)
    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])
    return status


@app.get("/tasks/{task_id}/result", response_model=TaskResultResponse)
async def get_task_result(
    task_id: str,
    orchestrator: Orchestrator = Depends(get_orchestrator_dep)
):
    """Get the complete result of a task."""
    result = await orchestrator.get_task_result(task_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.delete("/tasks/{task_id}", response_model=Dict[str, Any])
async def cancel_task(
    task_id: str,
    orchestrator: Orchestrator = Depends(get_orchestrator_dep)
):
    """Cancel a running task."""
    result = await orchestrator.cancel_task(task_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.websocket("/ws/tasks/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """WebSocket endpoint for real-time task updates."""
    await manager.connect(websocket, task_id)
    try:
        while True:
            # Keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, task_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
