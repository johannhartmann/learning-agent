"""HTTP bridge for proxying remote MCP server requests from sandbox."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx


logger = logging.getLogger(__name__)


class MCPHttpBridge:
    """Proxy HTTP requests from sandbox to remote MCP servers.

    This bridge runs on the host side and validates all requests from
    the Pyodide sandbox before forwarding to remote MCP servers.
    """

    def __init__(self, allowed_servers: dict[str, dict[str, Any]]):
        """Initialize MCP HTTP bridge.

        Args:
            allowed_servers: Mapping of server_name → config
                Example: {'browser': {'url': 'https://...', 'auth': {...}}}
        """
        self.allowed_servers = allowed_servers
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.server_clients: dict[str, Any] = {}

    async def get_server_config(self, server_name: str) -> dict[str, Any]:
        """Get configuration for a server.

        Args:
            server_name: Name of the server

        Returns:
            Server configuration dictionary

        Raises:
            ValueError: If server is not in allowed list
        """
        if server_name not in self.allowed_servers:
            raise ValueError(
                f"Server '{server_name}' not allowed. "
                f"Allowed servers: {list(self.allowed_servers.keys())}"
            )
        return self.allowed_servers[server_name]

    def _get_auth_token(self, auth_config: dict[str, Any] | None) -> str | None:
        """Extract authentication token from config.

        Args:
            auth_config: Authentication configuration

        Returns:
            Bearer token or None
        """
        if not auth_config:
            return None

        auth_type = auth_config.get("type")
        if auth_type == "bearer":
            token_env = auth_config.get("token_env")
            if token_env:
                return os.getenv(token_env)
            return auth_config.get("token")

        return None

    async def connect_server(self, server_name: str) -> Any:
        """Connect to a remote MCP server and return client.

        Args:
            server_name: Name of the server to connect to

        Returns:
            RemoteMCPClient instance

        Raises:
            ValueError: If server not allowed
        """
        # Return cached client if exists
        if server_name in self.server_clients:
            return self.server_clients[server_name]

        # Get server config
        config = await self.get_server_config(server_name)
        base_url = config["url"]
        auth_config = config.get("auth")
        auth_token = self._get_auth_token(auth_config)

        # Import here to avoid circular dependency
        from learning_agent.sandbox.remote_mcp_client import RemoteMCPClient

        # Create client
        client = RemoteMCPClient(base_url, auth_token)

        # Cache client
        self.server_clients[server_name] = client

        logger.info(f"Connected to remote MCP server: {server_name} at {base_url}")

        return client

    async def proxy_request(
        self,
        server_name: str,
        endpoint: str,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Proxy HTTP request to remote MCP server.

        Args:
            server_name: Name of the server
            endpoint: API endpoint (e.g., '/tools/list')
            method: HTTP method (GET or POST)
            data: Optional request body for POST

        Returns:
            JSON response from server

        Raises:
            ValueError: If server not allowed
            httpx.HTTPError: If request fails
        """
        # Validate server is allowed
        config = await self.get_server_config(server_name)
        base_url = config["url"]
        auth_config = config.get("auth")
        auth_token = self._get_auth_token(auth_config)

        # Build full URL
        url = f"{base_url.rstrip('/')}{endpoint}"

        # Build headers
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        # Make request
        if method.upper() == "GET":
            response = await self.http_client.get(url, headers=headers)
        elif method.upper() == "POST":
            response = await self.http_client.post(url, headers=headers, json=data)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        response.raise_for_status()
        return response.json()

    async def list_tools(self, server_name: str) -> list[dict[str, Any]]:
        """List available tools from remote MCP server.

        Args:
            server_name: Name of the server

        Returns:
            List of tool definitions
        """
        client = await self.connect_server(server_name)
        return await client.list_tools()

    async def list_resources(self, server_name: str) -> list[dict[str, Any]]:
        """List available resources from remote MCP server.

        Args:
            server_name: Name of the server

        Returns:
            List of resource definitions
        """
        client = await self.connect_server(server_name)
        return await client.list_resources()

    async def list_prompts(self, server_name: str) -> list[dict[str, Any]]:
        """List available prompts from remote MCP server.

        Args:
            server_name: Name of the server

        Returns:
            List of prompt definitions
        """
        client = await self.connect_server(server_name)
        return await client.list_prompts()

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Call a tool on remote MCP server.

        Args:
            server_name: Name of the server
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        client = await self.connect_server(server_name)
        return await client.call_tool(tool_name, arguments)

    async def read_resource(self, server_name: str, uri: str) -> dict[str, Any]:
        """Read a resource from remote MCP server.

        Args:
            server_name: Name of the server
            uri: Resource URI

        Returns:
            Resource content
        """
        client = await self.connect_server(server_name)
        return await client.read_resource(uri)

    async def get_prompt(
        self, server_name: str, prompt_name: str, arguments: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Get a prompt template from remote MCP server.

        Args:
            server_name: Name of the server
            prompt_name: Name of the prompt
            arguments: Optional prompt arguments

        Returns:
            Prompt content
        """
        client = await self.connect_server(server_name)
        return await client.get_prompt(prompt_name, arguments)

    async def close(self) -> None:
        """Close HTTP client and clean up resources."""
        await self.http_client.aclose()
        self.server_clients.clear()

    async def __aenter__(self) -> MCPHttpBridge:
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()
