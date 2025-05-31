from typing import List, Optional, Any, Dict
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings # Example embedding model

# Placeholder for settings if needed for API keys for embeddings
# from ..core.config_loader import settings # Adjust path as necessary

# A simple embedding class for testing if no external one is configured
class MockEmbeddings(Embeddings):
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # Simple hash-based embedding for consistent, but not meaningful, vectors
        return [[float(hash(text + str(i))) / (10**10)] * 10 for i, text in enumerate(texts)] # 10-dim vector

    def embed_query(self, text: str) -> List[float]:
        return [float(hash(text)) / (10**10)] * 10

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.embed_documents(texts)

    async def aembed_query(self, text: str) -> List[float]:
        return self.embed_query(text)


class VectorStoreManager:
    def __init__(self, embedding_service: Optional[Embeddings] = None, vector_store_path: Optional[str] = None):
        '''
        Manages a vector store (e.g., FAISS).

        Args:
            embedding_service: An instance of a Langchain Embeddings class.
                               If None, tries to initialize OpenAIEmbeddings or a MockEmbeddings.
            vector_store_path: Path to load/save a FAISS index. If None, operates in-memory.
        '''
        if embedding_service:
            self.embedding_service = embedding_service
        else:
            try:
                # Assuming OPENAI_API_KEY is in environment or settings
                # from langgraph_agent_project.core.config_loader import settings
                # openai_api_key = settings.OPENAI_API_KEY
                # For standalone, ensure key is in env or pass directly
                # For this example, we'll try to get it from env, but it's not robust for all contexts.
                import os
                openai_api_key = os.getenv("OPENAI_API_KEY")
                if not openai_api_key:
                    raise ValueError("OPENAI_API_KEY not found in environment.")
                self.embedding_service = OpenAIEmbeddings(openai_api_key=openai_api_key)
                print("VectorStoreManager: Initialized with OpenAIEmbeddings.")
            except Exception as e:
                print(f"VectorStoreManager: Failed to init OpenAIEmbeddings ({e}). Using MockEmbeddings.")
                self.embedding_service = MockEmbeddings()

        self.vector_store_path = vector_store_path
        self.vector_store: Optional[FAISS] = None

        if self.vector_store_path:
            try:
                # Attempt to load existing FAISS index
                self.vector_store = FAISS.load_local(
                    folder_path=self.vector_store_path,
                    embeddings=self.embedding_service,
                    allow_dangerous_deserialization=True # Required by recent Langchain/FAISS
                )
                print(f"VectorStoreManager: Loaded FAISS index from {self.vector_store_path}.")
            except Exception as e:
                print(f"VectorStoreManager: Failed to load FAISS index from {self.vector_store_path} ({e}). Will create new if documents are added.")
                self.vector_store = None
        else:
            print("VectorStoreManager: Initialized for in-memory FAISS store (no path provided).")

    def add_documents(self, documents: List[Document], **kwargs: Any) -> None:
        '''
        Adds documents to the vector store. Documents are embedded first.
        If the store is new or path-based and not loaded, it will be created/recreated.
        '''
        if not documents:
            print("VectorStoreManager: No documents provided to add.")
            return

        if self.vector_store is None:
            # Create new FAISS index
            try:
                self.vector_store = FAISS.from_documents(documents, self.embedding_service, **kwargs)
                print(f"VectorStoreManager: Created new FAISS index with {len(documents)} documents.")
            except Exception as e:
                print(f"VectorStoreManager: Error creating FAISS index: {e}")
                return
        else:
            # Add to existing FAISS index
            try:
                # FAISS.add_documents might return new doc ids, store them if needed
                self.vector_store.add_documents(documents, **kwargs)
                print(f"VectorStoreManager: Added {len(documents)} documents to existing FAISS index.")
            except Exception as e:
                print(f"VectorStoreManager: Error adding documents to FAISS: {e}")
                return

        if self.vector_store_path and self.vector_store:
            try:
                self.vector_store.save_local(self.vector_store_path)
                print(f"VectorStoreManager: Saved FAISS index to {self.vector_store_path}.")
            except Exception as e:
                print(f"VectorStoreManager: Error saving FAISS index to {self.vector_store_path}: {e}")


    def similarity_search(self, query: str, k: int = 4, **kwargs: Any) -> List[Document]:
        '''
        Performs a similarity search against the vector store.
        '''
        if self.vector_store is None:
            print("VectorStoreManager: No vector store initialized or documents added.")
            return []

        try:
            results = self.vector_store.similarity_search(query, k=k, **kwargs)
            print(f"VectorStoreManager: Found {len(results)} results for query '{query}'.")
            return results
        except Exception as e:
            print(f"VectorStoreManager: Error during similarity search: {e}")
            return []

    async def asimilarity_search(self, query: str, k: int = 4, **kwargs: Any) -> List[Document]:
        '''
        Asynchronously performs a similarity search.
        Note: FAISS itself is synchronous. This wraps the sync call.
        For truly async vector stores, the underlying library calls would be async.
        '''
        # Langchain's FAISS wrapper might not have a native async search.
        # We can run the synchronous search in a thread pool if needed for non-blocking behavior in async code.
        # For now, let's just call the sync version directly as many FAISS operations are CPU-bound.
        import asyncio # Import here for explicit use of to_thread if chosen
        if self.vector_store is None:
            print("VectorStoreManager (async): No vector store initialized.")
            return []
        try:
            # To make it truly non-blocking in an async context, use to_thread
            # results = await asyncio.to_thread(self.vector_store.similarity_search, query, k=k, **kwargs)
            # For simplicity, direct call for now, as FAISS is often used with CPU-bound tasks.
            # This means it will block the asyncio event loop if the search is long.
            results = self.vector_store.similarity_search(query, k=k, **kwargs)
            print(f"VectorStoreManager (async): Found {len(results)} results for query '{query}'.")
            return results
        except Exception as e:
            print(f"VectorStoreManager (async): Error during similarity search: {e}")
            return []


if __name__ == "__main__":
    print("--- VectorStoreManager Test ---")
    # This test assumes OpenAI API key is available for OpenAIEmbeddings,
    # or it will fall back to MockEmbeddings.
    # It also assumes `faiss-cpu` is installed.

    # Test with in-memory store first
    print("\n--- In-Memory FAISS Test ---")
    # To use OpenAIEmbeddings, ensure OPENAI_API_KEY is in your environment.
    # Forcing MockEmbeddings for this test to avoid API key dependency for basic run.
    mock_embeddings = MockEmbeddings()
    vs_manager_memory = VectorStoreManager(embedding_service=mock_embeddings)

    sample_docs_memory = [
        Document(page_content="LangGraph is a library for building stateful, multi-actor applications with LLMs.", metadata={"source": "doc1"}),
        Document(page_content="It extends LangChain and allows for cyclic graph structures.", metadata={"source": "doc2"}),
        Document(page_content="State management is a key feature of LangGraph.", metadata={"source": "doc3"}),
        Document(page_content="Python is a popular programming language.", metadata={"source": "doc4"}),
    ]
    vs_manager_memory.add_documents(sample_docs_memory)

    search_results_memory = vs_manager_memory.similarity_search("What is LangGraph?", k=2)
    print("Search Results (In-Memory):")
    for doc in search_results_memory:
        print(f"  Content: {doc.page_content}, Metadata: {doc.metadata}")

    # Test with persistent store (will create files in ./test_faiss_index)
    print("\n--- Persistent FAISS Test ---")
    import shutil
    import os # For path creation

    # Create path in current working directory for the test
    # Assuming /app is the cwd when run in sandbox
    test_faiss_path = os.path.join(os.getcwd(), "test_faiss_index")

    # Clean up previous test directory if it exists
    if os.path.exists(test_faiss_path):
        try:
            shutil.rmtree(test_faiss_path)
            print(f"Removed existing test directory: {test_faiss_path}")
        except Exception as e_rm:
            print(f"Error removing existing test directory {test_faiss_path}: {e_rm}")

    try:
        os.makedirs(test_faiss_path, exist_ok=True) # Ensure directory exists
        print(f"Ensured test directory exists: {test_faiss_path}")
    except Exception as e_mkdir:
        print(f"Error creating test directory {test_faiss_path}: {e_mkdir}")
        # If directory cannot be created, skip disk-based tests or handle error

    vs_manager_disk = VectorStoreManager(embedding_service=mock_embeddings, vector_store_path=test_faiss_path)
    sample_docs_disk = [
        Document(page_content="FastAPI is a modern web framework for Python.", metadata={"source": "web1"}),
        Document(page_content="Uvicorn is an ASGI server, commonly used with FastAPI.", metadata={"source": "web2"}),
    ]
    if vs_manager_disk.embedding_service: # Proceed only if embedding service is available
        vs_manager_disk.add_documents(sample_docs_disk)

        search_results_disk = vs_manager_disk.similarity_search("Web frameworks for Python", k=1)
        print("Search Results (Disk-based, first load):")
        for doc in search_results_disk:
            print(f"  Content: {doc.page_content}, Metadata: {doc.metadata}")

        # Test loading from disk
        print("\n--- Loading Persistent FAISS Test ---")
        vs_manager_disk_loaded = VectorStoreManager(embedding_service=mock_embeddings, vector_store_path=test_faiss_path)

        if vs_manager_disk_loaded.vector_store: # Check if store loaded successfully
            new_docs_for_disk = [Document(page_content="Pydantic is used for data validation.", metadata={"source": "lib1"})]
            vs_manager_disk_loaded.add_documents(new_docs_for_disk)

            search_results_disk_loaded = vs_manager_disk_loaded.similarity_search("data validation", k=1)
            print("Search Results (Disk-based, after load and add):")
            for doc in search_results_disk_loaded:
                print(f"  Content: {doc.page_content}, Metadata: {doc.metadata}")
        else:
            print("Skipping further disk tests as vector store did not load.")
    else:
        print("Skipping disk-based tests as embedding service failed to initialize.")


    # Clean up test directory - optional, might be good to inspect after run
    # try:
    #     if os.path.exists(test_faiss_path):
    #         shutil.rmtree(test_faiss_path)
    #         print(f"Cleaned up test directory: {test_faiss_path}")
    # except Exception as e_clean:
    #     print(f"Error cleaning up test directory {test_faiss_path}: {e_clean}")
    print(f"Test FAISS index may be present at: {test_faiss_path}. Manual cleanup might be desired.")
