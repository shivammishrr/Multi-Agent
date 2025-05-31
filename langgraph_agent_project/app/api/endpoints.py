from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import StreamingResponse
import json
from typing import List, Dict, Any, AsyncGenerator, Tuple # Added Tuple

# Assuming AgentManager and API models are accessible
# Adjust imports based on your project structure
try:
    from ..services.agent_manager import AgentManager
    from .models import InvokeAgentRequest, InvokeAgentResponse # StreamEventData
except ImportError:
    # Fallback for different execution context or if structure changes
    print("API Endpoints: Could not import AgentManager or API models. Using placeholders.")
    class AgentManager: # Placeholder
        def invoke_agent(self, user_input: str, conversation_history=None, config=None): return {"final_output": "mock sync output", "updated_conversation_history": []}
        async def ainvoke_agent(self, user_input: str, conversation_history=None, config=None): return {"final_output": "mock async output", "updated_conversation_history": []}
        async def stream_agent_responses(self, user_input: str, conversation_history=None, config=None):
            yield {"mock_node": {"data": "mock stream step"}}
            yield {"mock_node_2": {"final_data": "mock stream end"}}
            # Added async to placeholder stream
            if False: # make it an async generator
                yield

    class InvokeAgentRequest(BaseModel): # Placeholder using BaseModel for type hints
        user_input: str
        conversation_history: Optional[List[Tuple[str, str]]] = None
    class InvokeAgentResponse(BaseModel): # Placeholder
        final_output: Optional[str] = None
        updated_conversation_history: List[Tuple[str, str]]
        error: Optional[str] = None

    # Need to import BaseModel for placeholder if not already
    from pydantic import BaseModel
    import asyncio # For placeholder stream


# Initialize AgentManager (singleton or dependency injection)
# For simplicity, create a global instance here.
# In a larger app, use FastAPI's Depends for managing such dependencies.
agent_manager = AgentManager()

router = APIRouter()

@router.post("/invoke", response_model=InvokeAgentResponse)
async def invoke_agent_endpoint(request_data: InvokeAgentRequest = Body(...)):
    '''
    Synchronous (but non-blocking I/O) endpoint to invoke the agent.
    FastAPI runs sync functions in a thread pool.
    If AgentManager.invoke_agent is truly synchronous and CPU-bound,
    it might block. Prefer ainvoke_agent for FastAPI.
    Let's use ainvoke_agent for a truly async endpoint.
    '''
    try:
        # Use ainvoke_agent for better performance with FastAPI
        # The AgentManager.ainvoke_agent should prepare the initial state correctly
        final_state = await agent_manager.ainvoke_agent(
            user_input=request_data.user_input,
            conversation_history=request_data.conversation_history,
            # config=request_data.config # If config is added to request model
        )

        # Extract relevant info from the final state for the response
        # The structure of final_state depends on what AgentManager.ainvoke_agent returns,
        # which in turn depends on the LangGraph app's output.
        # Assuming it returns the full AgentState (a TypedDict).

        # Convert Langchain BaseMessages to simple tuples for conversation_history if needed
        # For now, assume agent_manager returns history in the desired format or
        # the graph itself stores messages as tuples.
        # The current AgentManager mock and graph setup uses simple tuples or string messages.

        history = final_state.get("messages", []) # This should be List[Tuple[str,str]] or convertable

        return InvokeAgentResponse(
            final_output=final_state.get("final_output"),
            updated_conversation_history=history,
            error=final_state.get("error_message")
        )
    except Exception as e:
        print(f"API Error in /invoke: {e}")
        # Log the exception details for debugging
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


async def stream_generator(user_input: str, conversation_history: List[Tuple[str,str]] | None) -> AsyncGenerator[str, None]:
    '''Generator function for streaming agent responses.'''
    async for step in agent_manager.stream_agent_responses( # Ensure this is an async generator
        user_input=user_input,
        conversation_history=conversation_history
    ):
        # Each 'step' is a dictionary like {node_name: node_output_state}
        # We need to serialize this to string for Server-Sent Events (SSE)
        # Typically, SSE events have `event: <name>` and `data: <json_string>`
        # For simplicity, just sending data lines for now.

        # Example: Wrap in a structure, then JSON dump
        # event_data = StreamEventData(node_name=list(step.keys())[0], node_output=list(step.values())[0])
        # yield f"data: {event_data.model_dump_json()}\n\n"

        # Simpler: just send the step directly as JSON
        yield f"data: {json.dumps(step)}\n\n" # SSE format: data: <json>


        await asyncio.sleep(0.01) # Small delay for demonstration, ensure client can keep up

@router.post("/stream") # Or @router.get("/stream") if params are via query
async def stream_agent_endpoint(request_data: InvokeAgentRequest = Body(...)):
    '''
    Endpoint to stream agent responses using Server-Sent Events (SSE).
    '''
    try:
        print(f"API /stream called with input: {request_data.user_input}")
        return StreamingResponse(
            stream_generator(request_data.user_input, request_data.conversation_history),
            media_type="text/event-stream"
        )
    except Exception as e:
        print(f"API Error in /stream: {e}")
        # Log the exception details
        import traceback
        traceback.print_exc()
        # StreamingResponse might have already started, so raising HTTPException might not work as expected.
        # It's better to handle errors within the generator if possible, or ensure setup fails before stream starts.
        # For now, this will catch errors during setup.
        raise HTTPException(status_code=500, detail=str(e))


# Simple test endpoint
@router.get("/ping")
async def ping():
    return {"message": "pong"}

if __name__ == "__main__":
    # This block is for testing the router setup, not for running the FastAPI app.
    # To run the app, you'd use uvicorn from main.py.
    print("API Router defined with /invoke, /stream, and /ping endpoints.")
    print("Testing model instantiation (not endpoint calls):")

    # Need pydantic.BaseModel for this test block if using placeholder InvokeAgentRequest
    from pydantic import BaseModel

    class InvokeAgentRequestTest(BaseModel): # Renamed to avoid conflict if real one is imported
        user_input: str
        conversation_history: Optional[List[Tuple[str, str]]] = None

    class InvokeAgentResponseTest(BaseModel): # Renamed
        final_output: Optional[str] = None
        updated_conversation_history: List[Tuple[str, str]]
        error: Optional[str] = None


    req = InvokeAgentRequestTest(user_input="Hello", conversation_history=[("human", "Hi"), ("ai", "Hello there")])
    print(f"Sample Request: {req.model_dump_json(indent=2)}")

    resp = InvokeAgentResponseTest(final_output="I am fine.", updated_conversation_history=[("human", "Hi"), ("ai", "Hello there"), ("human", "Hello"), ("ai", "I am fine.")])
    print(f"Sample Response: {resp.model_dump_json(indent=2)}")

    # To test endpoints, you need a running FastAPI application (e.g. using uvicorn)
    # and an HTTP client (like httpx or curl).
    # Example using httpx (if you were to run this in an async context with uvicorn programmatically):
    # import httpx
    # async def test_api():
    #     async with httpx.AsyncClient(app=your_fastapi_app_instance, base_url="http://127.0.0.1:8000") as client:
    #         ping_response = await client.get("/api/v1/ping") # Assuming router is prefixed
    #         print(ping_response.json())
    # asyncio.run(test_api())
