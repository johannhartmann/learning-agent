"""MCP namespace for sandbox code to access remote MCP APIs."""

from __future__ import annotations

from typing import Any


class MCPNamespace:
    """Provides mcp.server_name API access in sandbox code.

    Example usage in sandbox:
        browser = mcp.browser
        browser.goto("https://example.com")
        data = browser.extract_structured_data("headlines")
    """

    def __init__(self, apis: dict[str, Any]):
        """Initialize MCP namespace with API instances.

        Args:
            apis: Mapping of server_name → API instance
        """
        self._apis = apis

        # Expose APIs as attributes (convert hyphens to underscores)
        for name, api in apis.items():
            attr_name = name.replace("-", "_")
            setattr(self, attr_name, api)

    def list_servers(self) -> list[str]:
        """List available MCP servers.

        Returns:
            List of server names
        """
        return list(self._apis.keys())

    def __repr__(self) -> str:
        """String representation of MCP namespace."""
        servers = ", ".join(self._apis.keys())
        return f"<MCPNamespace servers=[{servers}]>"
