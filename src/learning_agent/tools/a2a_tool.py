"""A2A (Agent-to-Agent) communication tool for LangGraph Platform."""

import json
import logging
from typing import Any

import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from learning_agent.a2a_handler import format_a2a_request
from learning_agent.config import settings as get_settings


logger = logging.getLogger(__name__)


class A2AMessageInput(BaseModel):
    """Input schema for sending A2A messages."""

    agent_name: str = Field(description="Name of the target agent to communicate with")
    message: str = Field(description="Message to send to the other agent")
    thread_id: str | None = Field(
        default=None, description="Optional thread ID for conversation continuity"
    )
    checkpoint_id: str | None = Field(
        default=None, description="Optional checkpoint ID for state recovery"
    )
    interrupt: bool = Field(default=False, description="Whether to interrupt current execution")


class A2AClient:
    """Client for A2A communication with other agents."""

    def __init__(self, base_url: str | None = None):
        """Initialize A2A client.

        Args:
            base_url: Base URL for LangGraph server (defaults to settings)
        """
        self.base_url = base_url or getattr(get_settings, "langgraph_url", "http://localhost:8000")
        self.client = httpx.AsyncClient(timeout=30.0)

    async def send_message(
        self,
        agent_name: str,
        message: str,
        thread_id: str | None = None,
        checkpoint_id: str | None = None,
        interrupt: bool = False,
    ) -> dict[str, Any]:
        """Send an A2A message to another agent.

        Args:
            agent_name: Name of the target agent
            message: Message content
            thread_id: Optional thread ID
            checkpoint_id: Optional checkpoint ID
            interrupt: Whether to interrupt

        Returns:
            Response from the target agent
        """
        # Format the message as A2A request
        a2a_request = format_a2a_request(message)

        # Build the invocation payload
        payload: dict[str, Any] = {
            "assistant_id": agent_name,
            "input": a2a_request,
        }

        # Add optional parameters
        if thread_id:
            payload["thread_id"] = thread_id
        if checkpoint_id:
            payload["checkpoint_id"] = checkpoint_id
        if interrupt:
            payload["interrupt"] = interrupt

        # Send to the target agent's thread endpoint
        url = f"{self.base_url}/assistants/{agent_name}/invoke"

        try:
            response = await self.client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

            # Parse the response
            result = response.json()

            # Extract the actual message from the result
            if "output" in result and "result" in result["output"]:
                return dict(result["output"]["result"])

        except httpx.HTTPStatusError as e:
            logger.exception(f"HTTP error communicating with {agent_name}")
            return {"error": f"Failed to communicate with {agent_name}: {e}"}
        except Exception:
            logger.exception(f"Error sending A2A message to {agent_name}")
            return {"error": "Communication error"}
        else:
            return dict(result)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()


# Global client instance
_a2a_client: A2AClient | None = None


def get_a2a_client() -> A2AClient:
    """Get or create the global A2A client."""
    global _a2a_client
    if _a2a_client is None:
        _a2a_client = A2AClient()
    return _a2a_client


@tool
async def send_a2a_message(
    agent_name: str,
    message: str,
    thread_id: str | None = None,
    checkpoint_id: str | None = None,
    interrupt: bool = False,
) -> str:
    """Send a message to another agent using the A2A protocol.

    This tool enables communication between different agents running on the
    LangGraph platform. Messages are sent using the JSON-RPC format defined
    by the A2A specification.

    Args:
        agent_name: Name/ID of the target agent
        message: The message to send
        thread_id: Optional thread ID for conversation continuity
        checkpoint_id: Optional checkpoint ID for state recovery
        interrupt: Whether to interrupt the target agent's current execution

    Returns:
        Response from the target agent or error message
    """
    client = get_a2a_client()

    result = await client.send_message(
        agent_name=agent_name,
        message=message,
        thread_id=thread_id,
        checkpoint_id=checkpoint_id,
        interrupt=interrupt,
    )

    # Format response
    if "error" in result:
        return f"Error: {result['error']}"

    if "message" in result:
        msg = result["message"]
        if isinstance(msg, dict) and "parts" in msg:
            # Extract text from A2A message parts
            texts = [
                part.get("text", "") for part in msg.get("parts", []) if part.get("kind") == "text"
            ]
            return "\n".join(texts) if texts else "No response content"
        return str(msg)

    return json.dumps(result, indent=2)


# Export the tool
__all__ = ["A2AClient", "get_a2a_client", "send_a2a_message"]
