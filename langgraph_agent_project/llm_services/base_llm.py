from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Iterator, List, Dict
from langchain_core.messages import BaseMessage

class BaseLLMService(ABC):
    def __init__(self, api_key: str, model_name: str, **kwargs: Any):
        self.api_key = api_key
        self.model_name = model_name
        self.client = self._initialize_client(**kwargs)

    @abstractmethod
    def _initialize_client(self, **kwargs: Any) -> Any:
        '''Initializes the LLM client (e.g., OpenAI, Anthropic).'''
        pass

    @abstractmethod
    def invoke(self, prompt: str | List[BaseMessage], **kwargs: Any) -> Any:
        '''Synchronously invoke the LLM with a prompt or messages.'''
        pass

    @abstractmethod
    async def ainvoke(self, prompt: str | List[BaseMessage], **kwargs: Any) -> Any:
        '''Asynchronously invoke the LLM with a prompt or messages.'''
        pass

    @abstractmethod
    def stream(self, prompt: str | List[BaseMessage], **kwargs: Any) -> Iterator[Any]:
        '''Synchronously stream the LLM response.'''
        pass

    @abstractmethod
    async def astream(self, prompt: str | List[BaseMessage], **kwargs: Any) -> AsyncIterator[Any]:
        '''Asynchronously stream the LLM response.'''
        pass

    # Potentially add other common methods like model listing, token counting, etc.
