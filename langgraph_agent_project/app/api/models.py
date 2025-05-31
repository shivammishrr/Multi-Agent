from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Tuple

class InvokeAgentRequest(BaseModel):
    user_input: str
    conversation_history: Optional[List[Tuple[str, str]]] = None # e.g., [("human", "hi"), ("ai", "hello")]
    # config: Optional[Dict[str, Any]] = None # For graph config like recursion_limit

class InvokeAgentResponse(BaseModel):
    final_output: Optional[str] = None
    updated_conversation_history: List[Tuple[str, str]] # Full history including latest turn
    intermediate_steps: Optional[List[Dict[str, Any]]] = None # Optional: for debugging or rich UIs
    error: Optional[str] = None

# For streaming, the response type is different (Server-Sent Events or WebSockets)
# FastAPI handles this with StreamingResponse. Individual chunks could be structured.
class StreamEventData(BaseModel):
    node_name: str
    node_output: Dict[str, Any] # The state dictionary from the node
    # event_type: str # e.g., "thought", "tool_call", "tool_output", "final_response", "error"
