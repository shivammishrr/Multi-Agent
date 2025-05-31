from typing import Type, Optional, Any
import asyncio

from pydantic import BaseModel, Field

from tools.base_tool import BaseTool, BaseToolInput, BaseToolOutput

# No specific input schema needed beyond the base, but can be explicit for clarity
class TerminateToolInput(BaseToolInput):
    reason: Optional[str] = Field(default=None, description="An optional reason for termination.")

class TerminateToolOutput(BaseToolOutput):
    message: str = Field(..., description="Confirmation message for termination.")
    # 'output' from BaseToolOutput could carry the reason or a standard termination signal

class TerminateTool(BaseTool):
    name: str = "terminate_agent"
    description: str = ("Signals that the agent has completed its current task or should stop processing. "
                        "Use this when the objective is met or further action is not possible/required.")
    args_schema: Type[BaseModel] = TerminateToolInput
    return_schema: Type[BaseModel] = TerminateToolOutput

    def _run(self, reason: Optional[str] = None) -> TerminateToolOutput:
        termination_message = "Agent termination signaled."
        if reason:
            termination_message += f" Reason: {reason}"
        
        # The 'output' field in BaseToolOutput can be used to pass a special value
        # that the agent graph can interpret as a termination signal (e.g., END or a specific sentinel object).
        # For now, we'll just use a message.
        return TerminateToolOutput(message=termination_message, output="TERMINATE_SIGNAL") # output can be a more structured signal

    async def _arun(self, reason: Optional[str] = None) -> TerminateToolOutput:
        # Termination is usually a synchronous decision, but good to have async available.
        return self._run(reason=reason) # Simple wrapper for now

# Example Usage (for testing purposes):
# if __name__ == '__main__':
#     terminator = TerminateTool()

#     # Test with no reason
#     result1 = terminator.run()
#     print("--- Test 1 (No Reason) ---")
#     print(f"Message: {result1.message}")
#     print(f"Output Signal: {result1.output}")
#     print(f"Error: {result1.error}")

#     # Test with a reason
#     result2 = terminator.run(reason="Objective achieved successfully.")
#     print("\n--- Test 2 (With Reason) ---")
#     print(f"Message: {result2.message}")
#     print(f"Output Signal: {result2.output}")
#     print(f"Error: {result2.error}")

#     # Async test
#     async def main_async():
#         result_async = await terminator.arun(reason="Async termination test.")
#         print("\n--- Test 3 (Async) ---")
#         print(f"Message: {result_async.message}")
#         print(f"Output Signal: {result_async.output}")
#         print(f"Error: {result_async.error}")
    
#     asyncio.run(main_async())
