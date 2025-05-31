import uvicorn
from fastapi import FastAPI

# Import configuration loader and settings
# from .core.config_loader import settings # Relative import if main.py is treated as part of a package
# If main.py is run as a script, PYTHONPATH adjustments might be needed for these imports
# For simplicity, let's assume it can find 'core' and 'app' if run from project root.
try:
    from core.config_loader import settings
    from app.api.endpoints import router as api_router
    # from app.services.agent_manager import AgentManager # If you want to init here
    # from llm_services.openai_llm import OpenAILLMService # Example if initializing services here
    # from tools.tool_registry import ToolRegistry # Example
except ImportError as e:
    print(f"Error importing modules in main.py: {e}")
    print("Please ensure that the script is run from the project root directory (langgraph_agent_project)")
    print("and that all necessary __init__.py files are in place.")
    print("Using placeholder router if actual import failed.")
    from fastapi import APIRouter
    api_router = APIRouter()
    @api_router.get("/")
    async def fallback_root(): return {"message": "Fallback API: Actual router not loaded."}
    # Dummy settings if import fails
    class Settings:
        AGENT_NAME = "FallbackAgent"
    settings = Settings()


# Initialize FastAPI app
app = FastAPI(
    title=f"{settings.AGENT_NAME} API",
    description="API for interacting with the modular LangGraph AI agent.",
    version="0.1.0"
)

# Include the API router
# All routes defined in app.api.endpoints will be prefixed with /api/v1
app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["Root"])
async def read_root():
    return {
        "message": f"Welcome to the {settings.AGENT_NAME}. API documentation available at /docs or /redoc."
    }

# Main execution block to run the Uvicorn server
if __name__ == "__main__":
    print(f"Starting Uvicorn server for {settings.AGENT_NAME}...")
    # Configuration for Uvicorn.
    # Host "0.0.0.0" makes it accessible from network, "127.0.0.1" for local only.
    # Reload True is useful for development.
    uvicorn.run(
        "main:app",  # Points to the 'app' instance in this 'main.py' file
        host="0.0.0.0",
        port=8000,
        reload=True, # Automatically reloads server on code changes
        log_level="info"
    )

# Example of initializing global services (if not done elsewhere like in AgentManager or via FastAPI Depends)
# def initialize_global_services():
#     print("Initializing global services...")
#     # Load settings (already done above by import)
#     print(f"OpenAI API Key Loaded: {'Yes' if settings.OPENAI_API_KEY else 'No'}")
#
#     # Initialize LLM Services (example)
#     # openai_llm_service = OpenAILLMService(api_key=settings.OPENAI_API_KEY, model_name=settings.OPENAI_MODEL_NAME)
#     # print("OpenAILLMService initialized.")
#
#     # Initialize Tool Registry (example)
#     # tool_registry = ToolRegistry()
#     # from tools.web_search.search_tool import WebSearchTool # Example tool
#     # web_search_tool_instance = WebSearchTool()
#     # tool_registry.register_tool(web_search_tool_instance)
#     # print("ToolRegistry initialized and WebSearchTool registered.")
#
#     # Initialize Agent Manager (if it needs pre-loaded services)
#     # agent_manager = AgentManager(tool_registry=tool_registry, llm_service=openai_llm_service)
#     # print("AgentManager initialized with services.")
#     # This agent_manager instance would then need to be made available to the API endpoints,
#     # e.g., by passing it to the APIRouter or using FastAPI's dependency injection.
#     print("Global services initialization complete.")

# Call this function before app definition if services need to be ready globally.
# initialize_global_services()
