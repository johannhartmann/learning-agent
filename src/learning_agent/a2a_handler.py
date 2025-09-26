"""A2A (Agent-to-Agent) communication handler for LangGraph Platform.

This module implements the A2A protocol for enabling communication
between different agents using the JSON-RPC format.
"""

import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel


logger = logging.getLogger(__name__)


class A2APart(BaseModel):
    """A single part of an A2A message."""

    kind: str  # "text" for text messages
    text: str


class A2AMessage(BaseModel):
    """An A2A protocol message."""

    role: str  # "user" or "assistant"
    parts: list[A2APart]


class A2ARequest(BaseModel):
    """JSON-RPC request for A2A communication."""

    jsonrpc: str = "2.0"
    method: str  # "message/send"
    params: dict[str, Any]
    id: str | int | None = None


class A2AResponse(BaseModel):
    """JSON-RPC response for A2A communication."""

    jsonrpc: str = "2.0"
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    id: str | int | None = None


def convert_a2a_to_langchain_message(a2a_message: A2AMessage) -> HumanMessage | AIMessage:
    """Convert an A2A message to LangChain message format.

    Args:
        a2a_message: The A2A protocol message

    Returns:
        LangChain message (HumanMessage or AIMessage)
    """
    # Combine all text parts into a single message
    text_parts = [part.text for part in a2a_message.parts if part.kind == "text"]
    content = "\n".join(text_parts)

    # Map role to appropriate message type
    if a2a_message.role == "user":
        return HumanMessage(content=content)
    if a2a_message.role == "assistant":
        return AIMessage(content=content)
    # Default to HumanMessage for unknown roles
    logger.warning(f"Unknown A2A message role: {a2a_message.role}, treating as user")
    return HumanMessage(content=content)


def convert_langchain_to_a2a_message(message: HumanMessage | AIMessage) -> A2AMessage:
    """Convert a LangChain message to A2A message format.

    Args:
        message: LangChain message

    Returns:
        A2A protocol message
    """
    # Determine role based on message type
    if isinstance(message, HumanMessage):
        role = "user"
    else:  # AIMessage
        role = "assistant"

    # Create text part from message content
    content = message.content if isinstance(message.content, str) else str(message.content)
    parts = [A2APart(kind="text", text=content)]

    return A2AMessage(role=role, parts=parts)


async def process_a2a_request(request: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    """Process an incoming A2A request.

    Args:
        request: Raw JSON-RPC request
        state: Current agent state

    Returns:
        Updated state with new message added
    """
    try:
        # Parse the request
        a2a_request = A2ARequest(**request)

        # Handle message/send method
        if a2a_request.method != "message/send":
            logger.warning(f"Unknown A2A method: {a2a_request.method}")
            return state

        # Extract the message
        message_data = a2a_request.params.get("message", {})
        a2a_message = A2AMessage(**message_data)

        # Convert to LangChain format
        lc_message = convert_a2a_to_langchain_message(a2a_message)

        # Add to state messages
        messages = state.get("messages", [])
        messages.append(lc_message)

        logger.info(f"Processed A2A message from {a2a_message.role}: {lc_message.content[:100]}...")

    except Exception as e:
        logger.error(f"Error processing A2A request: {e}", exc_info=True)
        return state
    else:
        return {"messages": messages}


def create_a2a_response(messages: list[Any], request_id: str | int | None = None) -> A2AResponse:
    """Create an A2A response from agent messages.

    Args:
        messages: List of messages from the agent
        request_id: Optional request ID for correlation

    Returns:
        A2A response object
    """
    if not messages:
        return A2AResponse(
            result={"status": "no_response"},
            id=request_id,
        )

    # Get the last AI message as the response
    last_ai_message = None
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            last_ai_message = msg
            break

    if last_ai_message:
        a2a_message = convert_langchain_to_a2a_message(last_ai_message)
        return A2AResponse(
            result={
                "message": a2a_message.dict(),
                "status": "success",
            },
            id=request_id,
        )
    return A2AResponse(
        result={"status": "no_ai_response"},
        id=request_id,
    )


def format_a2a_request(message: str, method: str = "message/send") -> dict[str, Any]:
    """Format a message as an A2A request.

    Args:
        message: The message text to send
        method: The A2A method (default: "message/send")

    Returns:
        Formatted A2A request dictionary
    """
    return {
        "jsonrpc": "2.0",
        "method": method,
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": message}],
            }
        },
    }
