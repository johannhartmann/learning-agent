"""Remote MCP client for HTTP/SSE transport in Pyodide sandbox."""

from __future__ import annotations

import json
from typing import Any


class RemoteMCPClient:
    """HTTP-based MCP client for remote servers.

    This client runs inside the Pyodide sandbox and communicates with
    remote MCP servers via HTTP/SSE transport.
    """

    def __init__(self, base_url: str, auth_token: str | None = None):
        """Initialize remote MCP client.

        Args:
            base_url: Base URL of remote MCP server (e.g., https://mcp.example.com)
            auth_token: Optional Bearer token for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
        self.session_id: str | None = None

    def _headers(self) -> dict[str, str]:
        """Build HTTP headers with authentication."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    async def list_tools(self) -> list[dict[str, Any]]:
        """Fetch available tools from remote MCP server.

        Returns:
            List of tool definitions with name, description, and inputSchema
        """
        # In Pyodide, use pyodide.http.pyfetch
        try:
            from pyodide.http import pyfetch  # type: ignore[import-not-found]
        except ImportError:
            # Fallback for non-Pyodide environments (testing)
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.base_url}/tools/list", headers=self._headers())
                return response.json()

        response = await pyfetch(
            f"{self.base_url}/tools/list", method="GET", headers=self._headers()
        )

        data = await response.json()
        return data.get("tools", [])

    async def list_resources(self) -> list[dict[str, Any]]:
        """Fetch available resources from remote MCP server.

        Returns:
            List of resource definitions with uri, name, description, mimeType
        """
        try:
            from pyodide.http import pyfetch  # type: ignore[import-not-found]
        except ImportError:
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/resources/list", headers=self._headers()
                )
                return response.json()

        response = await pyfetch(
            f"{self.base_url}/resources/list", method="GET", headers=self._headers()
        )

        data = await response.json()
        return data.get("resources", [])

    async def list_prompts(self) -> list[dict[str, Any]]:
        """Fetch available prompts from remote MCP server.

        Returns:
            List of prompt definitions with name, description, arguments
        """
        try:
            from pyodide.http import pyfetch  # type: ignore[import-not-found]
        except ImportError:
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/prompts/list", headers=self._headers()
                )
                return response.json()

        response = await pyfetch(
            f"{self.base_url}/prompts/list", method="GET", headers=self._headers()
        )

        data = await response.json()
        return data.get("prompts", [])

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Invoke a tool on the remote MCP server.

        Args:
            name: Tool name to invoke
            arguments: Tool arguments as dictionary

        Returns:
            Tool execution result
        """
        try:
            from pyodide.http import pyfetch  # type: ignore[import-not-found]
        except ImportError:
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/tools/call",
                    headers=self._headers(),
                    json={"name": name, "arguments": arguments},
                )
                return response.json()

        response = await pyfetch(
            f"{self.base_url}/tools/call",
            method="POST",
            headers=self._headers(),
            body=json.dumps({"name": name, "arguments": arguments}),
        )

        data = await response.json()
        return data.get("content", [])

    async def read_resource(self, uri: str) -> dict[str, Any]:
        """Read a resource from the remote MCP server.

        Args:
            uri: Resource URI to read

        Returns:
            Resource content
        """
        try:
            from pyodide.http import pyfetch  # type: ignore[import-not-found]
        except ImportError:
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/resources/read", headers=self._headers(), json={"uri": uri}
                )
                return response.json()

        response = await pyfetch(
            f"{self.base_url}/resources/read",
            method="POST",
            headers=self._headers(),
            body=json.dumps({"uri": uri}),
        )

        data = await response.json()
        return data

    async def get_prompt(
        self, name: str, arguments: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Get a prompt template from the remote MCP server.

        Args:
            name: Prompt name
            arguments: Optional prompt arguments for substitution

        Returns:
            Prompt content with messages
        """
        try:
            from pyodide.http import pyfetch  # type: ignore[import-not-found]
        except ImportError:
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/prompts/get",
                    headers=self._headers(),
                    json={"name": name, "arguments": arguments or {}},
                )
                return response.json()

        response = await pyfetch(
            f"{self.base_url}/prompts/get",
            method="POST",
            headers=self._headers(),
            body=json.dumps({"name": name, "arguments": arguments or {}}),
        )

        data = await response.json()
        return data
