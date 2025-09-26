"""Tests for A2A (Agent-to-Agent) communication functionality."""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from learning_agent.a2a_handler import (
    A2AMessage,
    A2APart,
    convert_a2a_to_langchain_message,
    convert_langchain_to_a2a_message,
    create_a2a_response,
    format_a2a_request,
    process_a2a_request,
)


class TestA2AConversion:
    """Test message conversion between A2A and LangChain formats."""

    def test_convert_a2a_user_to_langchain(self):
        """Test converting A2A user message to HumanMessage."""
        a2a_msg = A2AMessage(
            role="user",
            parts=[A2APart(kind="text", text="Hello, agent!")],
        )

        lc_msg = convert_a2a_to_langchain_message(a2a_msg)

        assert isinstance(lc_msg, HumanMessage)
        assert lc_msg.content == "Hello, agent!"

    def test_convert_a2a_assistant_to_langchain(self):
        """Test converting A2A assistant message to AIMessage."""
        a2a_msg = A2AMessage(
            role="assistant",
            parts=[A2APart(kind="text", text="Hello, user!")],
        )

        lc_msg = convert_a2a_to_langchain_message(a2a_msg)

        assert isinstance(lc_msg, AIMessage)
        assert lc_msg.content == "Hello, user!"

    def test_convert_a2a_multiple_parts(self):
        """Test converting A2A message with multiple text parts."""
        a2a_msg = A2AMessage(
            role="user",
            parts=[
                A2APart(kind="text", text="Part 1"),
                A2APart(kind="text", text="Part 2"),
            ],
        )

        lc_msg = convert_a2a_to_langchain_message(a2a_msg)

        assert lc_msg.content == "Part 1\nPart 2"

    def test_convert_langchain_human_to_a2a(self):
        """Test converting HumanMessage to A2A format."""
        lc_msg = HumanMessage(content="Test message")

        a2a_msg = convert_langchain_to_a2a_message(lc_msg)

        assert a2a_msg.role == "user"
        assert len(a2a_msg.parts) == 1
        assert a2a_msg.parts[0].kind == "text"
        assert a2a_msg.parts[0].text == "Test message"

    def test_convert_langchain_ai_to_a2a(self):
        """Test converting AIMessage to A2A format."""
        lc_msg = AIMessage(content="Response message")

        a2a_msg = convert_langchain_to_a2a_message(lc_msg)

        assert a2a_msg.role == "assistant"
        assert len(a2a_msg.parts) == 1
        assert a2a_msg.parts[0].kind == "text"
        assert a2a_msg.parts[0].text == "Response message"


class TestA2ARequest:
    """Test A2A request processing."""

    @pytest.mark.asyncio
    async def test_process_a2a_message_send(self):
        """Test processing a message/send A2A request."""
        request = {
            "jsonrpc": "2.0",
            "method": "message/send",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{"kind": "text", "text": "Process this"}],
                }
            },
            "id": 1,
        }
        state = {"messages": []}

        result = await process_a2a_request(request, state)

        assert "messages" in result
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], HumanMessage)
        assert result["messages"][0].content == "Process this"

    @pytest.mark.asyncio
    async def test_process_a2a_unknown_method(self):
        """Test processing an unknown A2A method."""
        request = {
            "jsonrpc": "2.0",
            "method": "unknown/method",
            "params": {},
            "id": 1,
        }
        state = {"messages": []}

        with patch("learning_agent.a2a_handler.logger") as mock_logger:
            result = await process_a2a_request(request, state)

            assert result == state
            mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_a2a_invalid_request(self):
        """Test processing an invalid A2A request."""
        request = {"invalid": "request"}
        state = {"messages": []}

        with patch("learning_agent.a2a_handler.logger") as mock_logger:
            result = await process_a2a_request(request, state)

            assert result == state
            mock_logger.error.assert_called_once()


class TestA2AResponse:
    """Test A2A response creation."""

    def test_create_a2a_response_with_ai_message(self):
        """Test creating A2A response from messages with AI message."""
        messages = [
            HumanMessage(content="Question"),
            AIMessage(content="Answer"),
        ]

        response = create_a2a_response(messages, request_id=123)

        assert response.jsonrpc == "2.0"
        assert response.id == 123
        assert response.result is not None
        assert response.error is None
        assert response.result["status"] == "success"
        assert "message" in response.result
        assert response.result["message"]["role"] == "assistant"
        assert response.result["message"]["parts"][0]["text"] == "Answer"

    def test_create_a2a_response_no_ai_message(self):
        """Test creating A2A response when no AI message exists."""
        messages = [HumanMessage(content="Question")]

        response = create_a2a_response(messages, request_id=456)

        assert response.result["status"] == "no_ai_response"
        assert response.id == 456

    def test_create_a2a_response_empty_messages(self):
        """Test creating A2A response with empty messages."""
        messages = []

        response = create_a2a_response(messages)

        assert response.result["status"] == "no_response"


class TestA2AHelpers:
    """Test A2A helper functions."""

    def test_format_a2a_request(self):
        """Test formatting a message as an A2A request."""
        message = "Test message"

        request = format_a2a_request(message)

        assert request["jsonrpc"] == "2.0"
        assert request["method"] == "message/send"
        assert request["params"]["message"]["role"] == "user"
        assert request["params"]["message"]["parts"][0]["kind"] == "text"
        assert request["params"]["message"]["parts"][0]["text"] == "Test message"

    def test_format_a2a_request_custom_method(self):
        """Test formatting with custom method."""
        message = "Custom message"
        method = "custom/method"

        request = format_a2a_request(message, method)

        assert request["method"] == "custom/method"


@pytest.mark.asyncio
class TestA2ATool:
    """Test A2A tool functionality."""

    async def test_send_a2a_message_success(self):
        """Test successful A2A message sending."""
        from learning_agent.tools.a2a_tool import A2AClient

        client = A2AClient("http://test-server:8000")

        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "output": {
                "result": {
                    "message": {
                        "role": "assistant",
                        "parts": [{"kind": "text", "text": "Response"}],
                    },
                    "status": "success",
                }
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client.client, "post", return_value=mock_response) as mock_post:
            mock_post.return_value = mock_response

            result = await client.send_message(
                agent_name="test-agent",
                message="Test message",
                thread_id="thread-123",
            )

            assert result["status"] == "success"
            assert "message" in result

    async def test_send_a2a_message_http_error(self):
        """Test A2A message sending with HTTP error."""
        from httpx import HTTPStatusError, Request, Response

        from learning_agent.tools.a2a_tool import A2AClient

        client = A2AClient("http://test-server:8000")

        request = Request("POST", "http://test-server:8000")
        response = Response(404, request=request)
        error = HTTPStatusError("Not Found", request=request, response=response)

        with patch.object(client.client, "post", side_effect=error):
            result = await client.send_message(
                agent_name="test-agent",
                message="Test message",
            )

            assert "error" in result
            assert "Failed to communicate" in result["error"]
