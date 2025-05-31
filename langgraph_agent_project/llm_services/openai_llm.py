from typing import Any, AsyncIterator, Iterator, List, Optional, cast
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration

from .base_llm import BaseLLMService
# Assuming settings are accessible, e.g., from langgraph_agent_project.core.config_loader import settings
# For now, we'll pass api_key and model_name directly or assume they are set in env
# from ..core.config_loader import settings # This might cause circular import if base_llm needs config

class OpenAILLMService(BaseLLMService):
    def _initialize_client(self, **kwargs: Any) -> ChatOpenAI:
        # `api_key` and `model_name` are from the constructor
        client = ChatOpenAI(
            api_key=self.api_key,
            model=self.model_name,
            temperature=kwargs.get("temperature", 0.7),
            # Add other OpenAI specific params from kwargs if needed
            **kwargs.get("client_kwargs", {})
        )
        return client

    def invoke(self, prompt: str | List[BaseMessage], **kwargs: Any) -> AIMessage:
        if not isinstance(self.client, ChatOpenAI):
            raise TypeError("Client is not an instance of ChatOpenAI")
        # Langchain's ChatOpenAI expects List[BaseMessage] for chat models
        # If a string prompt is given, it should be wrapped, e.g. in HumanMessage
        # For simplicity, this example will assume messages are passed correctly by the caller
        # or the caller uses a Langchain Runnable sequence that handles it.
        # For direct use, the caller must ensure `prompt` is `List[BaseMessage]`.
        return self.client.invoke(prompt, **kwargs)

    async def ainvoke(self, prompt: str | List[BaseMessage], **kwargs: Any) -> AIMessage:
        if not isinstance(self.client, ChatOpenAI):
            raise TypeError("Client is not an instance of ChatOpenAI")
        return await self.client.ainvoke(prompt, **kwargs)

    def stream(self, prompt: str | List[BaseMessage], **kwargs: Any) -> Iterator[BaseMessage]:
        if not isinstance(self.client, ChatOpenAI):
            raise TypeError("Client is not an instance of ChatOpenAI")
        return self.client.stream(prompt, **kwargs)

    async def astream(self, prompt: str | List[BaseMessage], **kwargs: Any) -> AsyncIterator[BaseMessage]:
        if not isinstance(self.client, ChatOpenAI):
            raise TypeError("Client is not an instance of ChatOpenAI")
        return self.client.astream(prompt, **kwargs)

# Example Usage (for testing this file directly)
if __name__ == "__main__":
    import asyncio
    from langchain_core.messages import HumanMessage, SystemMessage
    # Ensure OPENAI_API_KEY is set in your environment or a .env file
    # that your config_loader would pick up (if settings were used here)
    # For this direct test, it must be in the environment.
    # You might need to run: export OPENAI_API_KEY="your_key"

    try:
        openai_service = OpenAILLMService(api_key="YOUR_OPENAI_API_KEY", model_name="gpt-3.5-turbo") # Replace with your key or load from env

        messages = [
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content="What is the capital of France?")
        ]

        # Synchronous invoke
        print("--- Synchronous Invoke ---")
        response = openai_service.invoke(messages)
        print(response.content)

        # Asynchronous invoke
        async def run_ainvoke():
            print("\n--- Asynchronous Invoke ---")
            response_async = await openai_service.ainvoke(messages)
            print(response_async.content)
        asyncio.run(run_ainvoke())

        # Synchronous stream
        print("\n--- Synchronous Stream ---")
        for chunk in openai_service.stream(messages):
            print(chunk.content, end="", flush=True)
        print()

        # Asynchronous stream
        async def run_astream():
            print("\n--- Asynchronous Stream ---")
            async for chunk in openai_service.astream(messages):
                print(chunk.content, end="", flush=True)
            print()
        asyncio.run(run_astream())

    except Exception as e:
        print(f"An error occurred: {e}")
        print("Please ensure your OPENAI_API_KEY is correctly set as an environment variable.")
