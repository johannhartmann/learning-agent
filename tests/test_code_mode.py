"""Tests for MCP code-mode integration."""

import pytest

from learning_agent.sandbox.api_generator import (
    generate_api_class,
    generate_method,
    json_schema_to_python_type,
    snake_to_pascal,
)


class TestCodeModeHelpers:
    """Test helper functions for code-mode."""

    def test_snake_to_pascal(self):
        """Test snake_case to PascalCase conversion."""
        assert snake_to_pascal("browser") == "Browser"
        assert snake_to_pascal("browser_use") == "BrowserUse"
        assert snake_to_pascal("my-server-name") == "MyServerName"

    def test_json_schema_to_python_type(self):
        """Test JSON Schema to Python type conversion."""
        # Basic types
        assert json_schema_to_python_type({"type": "string"}, required=True) == "str"
        assert json_schema_to_python_type({"type": "integer"}, required=True) == "int"
        assert json_schema_to_python_type({"type": "number"}, required=True) == "float"
        assert json_schema_to_python_type({"type": "boolean"}, required=True) == "bool"

        # Optional types
        assert json_schema_to_python_type({"type": "string"}, required=False) == "str | None"

        # Enum types
        result = json_schema_to_python_type(
            {"type": "string", "enum": ["load", "domcontentloaded"]}, required=True
        )
        assert result == 'Literal["load", "domcontentloaded"]'

        # Array types
        assert (
            json_schema_to_python_type(
                {"type": "array", "items": {"type": "string"}}, required=True
            )
            == "list[str]"
        )

        # Object types
        assert json_schema_to_python_type({"type": "object"}, required=True) == "dict[str, Any]"


class TestAPIGenerator:
    """Test API generation from MCP schemas."""

    def test_generate_method(self):
        """Test method generation from tool schema."""
        tool = {
            "name": "goto",
            "description": "Navigate to a URL",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to navigate to"},
                    "wait_until": {
                        "type": "string",
                        "description": "Wait condition",
                        "enum": ["load", "domcontentloaded"],
                    },
                },
                "required": ["url"],
            },
        }

        method_code = generate_method(tool)

        # Check method includes async def
        assert "async def goto" in method_code

        # Check parameters
        assert "url: str" in method_code
        assert 'wait_until: Literal["load", "domcontentloaded"] | None = None' in method_code

        # Check docstring
        assert "Navigate to a URL" in method_code
        assert "Args:" in method_code

        # Check body calls client
        assert "await self._client.call_tool" in method_code

    @pytest.mark.asyncio
    async def test_generate_api_class(self):
        """Test API class generation."""
        tools = [
            {
                "name": "goto",
                "description": "Navigate to a URL",
                "inputSchema": {
                    "type": "object",
                    "properties": {"url": {"type": "string"}},
                    "required": ["url"],
                },
            },
            {
                "name": "screenshot",
                "description": "Take a screenshot",
                "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}},
            },
        ]

        class_code = await generate_api_class("browser", "https://browser-mcp.example.com", tools)

        # Check class definition
        assert "class BrowserAPI:" in class_code
        assert '"""Remote MCP: https://browser-mcp.example.com"""' in class_code

        # Check imports
        assert "from typing import Any, Literal" in class_code

        # Check __init__
        assert "def __init__(self, client: Any):" in class_code

        # Check methods exist
        assert "async def goto" in class_code
        assert "async def screenshot" in class_code


@pytest.mark.asyncio
class TestMCPHttpBridge:
    """Test MCP HTTP bridge."""

    async def test_bridge_initialization(self):
        """Test bridge initialization with server configs."""
        from learning_agent.sandbox.mcp_http_bridge import MCPHttpBridge

        servers = {
            "browser": {
                "url": "https://browser.example.com",
                "auth": {"type": "bearer", "token": "test-token"},
            }
        }

        bridge = MCPHttpBridge(servers)
        assert "browser" in bridge.allowed_servers
        assert bridge.allowed_servers["browser"]["url"] == "https://browser.example.com"

    async def test_get_server_config(self):
        """Test server config retrieval."""
        from learning_agent.sandbox.mcp_http_bridge import MCPHttpBridge

        servers = {"browser": {"url": "https://browser.example.com"}}

        bridge = MCPHttpBridge(servers)
        config = await bridge.get_server_config("browser")
        assert config["url"] == "https://browser.example.com"

        # Test invalid server
        with pytest.raises(ValueError, match="not allowed"):
            await bridge.get_server_config("invalid")


class TestMCPNamespace:
    """Test MCP namespace helper."""

    def test_namespace_creation(self):
        """Test namespace creation with APIs."""
        from learning_agent.sandbox.mcp_namespace import MCPNamespace

        class MockBrowserAPI:
            pass

        class MockFilesystemAPI:
            pass

        apis = {"browser": MockBrowserAPI(), "filesystem": MockFilesystemAPI()}

        namespace = MCPNamespace(apis)

        # Check APIs are accessible
        assert hasattr(namespace, "browser")
        assert hasattr(namespace, "filesystem")
        assert isinstance(namespace.browser, MockBrowserAPI)
        assert isinstance(namespace.filesystem, MockFilesystemAPI)

        # Check list_servers
        assert sorted(namespace.list_servers()) == ["browser", "filesystem"]

    def test_namespace_hyphen_conversion(self):
        """Test hyphenated server names convert to underscores."""
        from learning_agent.sandbox.mcp_namespace import MCPNamespace

        class MockAPI:
            pass

        apis = {"browser-use": MockAPI()}

        namespace = MCPNamespace(apis)

        # Hyphen should be converted to underscore
        assert hasattr(namespace, "browser_use")
        assert isinstance(namespace.browser_use, MockAPI)
