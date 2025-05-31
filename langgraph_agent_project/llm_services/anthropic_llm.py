from typing import Any, AsyncIterator, Iterator, List, Optional, cast
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, AIMessage
# from ..core.config_loader import settings # Potential circular import

from .base_llm import BaseLLMService

class AnthropicLLMService(BaseLLMService):
    def _initialize_client(self, **kwargs: Any) -> ChatAnthropic:
        client = ChatAnthropic(
            api_key=self.api_key,
            model=self.model_name,
            temperature=kwargs.get("temperature", 0.7),
            **kwargs.get("client_kwargs", {})
        )
        return client

    def invoke(self, prompt: str | List[BaseMessage], **kwargs: Any) -> AIMessage:
        if not isinstance(self.client, ChatAnthropic):
            raise TypeError("Client is not an instance of ChatAnthropic")
        return self.client.invoke(prompt, **kwargs)

    async def ainvoke(self, prompt: str | List[BaseMessage], **kwargs: Any) -> AIMessage:
        if not isinstance(self.client, ChatAnthropic):
            raise TypeError("Client is not an instance of ChatAnthropic")
        return await self.client.ainvoke(prompt, **kwargs)

    def stream(self, prompt: str | List[BaseMessage], **kwargs: Any) -> Iterator[BaseMessage]:
        if not isinstance(self.client, ChatAnthropic):
            raise TypeError("Client is not an instance of ChatAnthropic")
        return self.client.stream(prompt, **kwargs)

    async def astream(self, prompt: str | List[BaseMessage], **kwargs: Any) -> AsyncIterator[BaseMessage]:
        if not isinstance(self.client, ChatAnthropic):
            raise TypeError("Client is not an instance of ChatAnthropic")
        return self.client.astream(prompt, **kwargs)

# Example Usage (for testing this file directly)
if __name__ == "__main__":
    import asyncio
    from langchain_core.messages import HumanMessage, SystemMessage
    # Ensure ANTHROPIC_API_KEY is set in your environment
    # export ANTHROPIC_API_KEY="your_key"

    try:
        # Replace with your key or ensure it's in env for the test
        anthropic_service = AnthropicLLMService(api_key="YOUR_ANTHROPIC_API_KEY", model_name="claude-3-opus-20240229") # Or claude-2 etc.

        messages = [
            SystemMessage(content="You are a helpful assistant that speaks like a pirate."),
            HumanMessage(content="What be the finest treasure?")
        ]

        # Synchronous invoke
        print("--- Synchronous Invoke (Anthropic) ---")
        response = anthropic_service.invoke(messages)
        print(response.content)

        # Asynchronous invoke
        async def run_ainvoke_anthropic():
            print("\n--- Asynchronous Invoke (Anthropic) ---")
            response_async = await anthropic_service.ainvoke(messages)
            print(response_async.content)
        asyncio.run(run_ainvoke_anthropic())

        # Synchronous stream
        print("\n--- Synchronous Stream (Anthropic) ---")
        for chunk in anthropic_service.stream(messages):
            print(chunk.content, end="", flush=True)
        print()

        # Asynchronous stream
        async def run_astream_anthropic():
            print("\n--- Asynchronous Stream (Anthropic) ---")
            async for chunk in anthropic_service.astream(messages):
                print(chunk.content, end="", flush=True)
            print()
        asyncio.run(run_astream_anthropic())

    except Exception as e:
        print(f"An error occurred with Anthropic service: {e}")
        print("Please ensure your ANTHROPIC_API_KEY is correctly set as an environment variable.")
