"""Generate Python API code from MCP tool schemas."""

from __future__ import annotations

from typing import Any


def snake_to_pascal(snake_str: str) -> str:
    """Convert snake_case to PascalCase.

    Args:
        snake_str: String in snake_case format

    Returns:
        String in PascalCase format
    """
    components = snake_str.replace("-", "_").split("_")
    return "".join(x.title() for x in components)


def json_schema_to_python_type(schema: dict[str, Any], required: bool = False) -> str:
    """Convert JSON Schema type to Python type hint.

    Args:
        schema: JSON Schema property definition
        required: Whether the parameter is required

    Returns:
        Python type hint string
    """
    schema_type = schema.get("type", "any")
    enum = schema.get("enum")

    # Handle enum types
    if enum:
        enum_values = ", ".join(f'"{v}"' for v in enum)
        type_hint = f"Literal[{enum_values}]"
    # Handle basic types
    elif schema_type == "string":
        type_hint = "str"
    elif schema_type == "integer":
        type_hint = "int"
    elif schema_type == "number":
        type_hint = "float"
    elif schema_type == "boolean":
        type_hint = "bool"
    elif schema_type == "array":
        items = schema.get("items", {})
        item_type = json_schema_to_python_type(items, required=True)
        type_hint = f"list[{item_type}]"
    elif schema_type == "object":
        type_hint = "dict[str, Any]"
    else:
        type_hint = "Any"

    # Make optional if not required
    if not required:
        type_hint = f"{type_hint} | None"

    return type_hint


def generate_method_signature(tool: dict[str, Any]) -> tuple[str, list[str], str]:
    """Generate method signature from tool schema.

    Args:
        tool: MCP tool definition

    Returns:
        Tuple of (method_name, param_lines, return_type)
    """
    name = tool.get("name", "unknown_tool")
    schema = tool.get("inputSchema", {})
    properties = schema.get("properties", {})
    required_params = set(schema.get("required", []))

    # Generate parameters
    param_lines = ["self"]
    for param_name, param_schema in properties.items():
        is_required = param_name in required_params
        type_hint = json_schema_to_python_type(param_schema, required=is_required)

        if is_required:
            param_lines.append(f"{param_name}: {type_hint}")
        else:
            param_lines.append(f"{param_name}: {type_hint} = None")

    return name, param_lines, "dict[str, Any]"


def generate_method_docstring(tool: dict[str, Any]) -> str:
    """Generate docstring from tool schema.

    Args:
        tool: MCP tool definition

    Returns:
        Formatted docstring
    """
    description = tool.get("description", "")
    schema = tool.get("inputSchema", {})
    properties = schema.get("properties", {})

    # Build docstring
    lines = [f'"""{description}']

    if properties:
        lines.append("")
        lines.append("Args:")
        for param_name, param_schema in properties.items():
            param_desc = param_schema.get("description", "")
            lines.append(f"    {param_name}: {param_desc}")

    lines.append("")
    lines.append("Returns:")
    lines.append("    Tool execution result")
    lines.append('"""')

    return "\n        ".join(lines)


def generate_method_body(tool: dict[str, Any]) -> str:
    """Generate method body that calls remote MCP client.

    Args:
        tool: MCP tool definition

    Returns:
        Method body code
    """
    name = tool.get("name", "unknown_tool")
    schema = tool.get("inputSchema", {})
    properties = schema.get("properties", {})

    # Build arguments dictionary
    args_lines = [f'"{param_name}": {param_name}' for param_name in properties]

    if args_lines:
        args_dict = "{\n            " + ",\n            ".join(args_lines) + "\n        }"
    else:
        args_dict = "{}"

    # Remove None values from arguments
    body = f"""arguments = {args_dict}
        # Remove None values
        arguments = {{k: v for k, v in arguments.items() if v is not None}}
        return await self._client.call_tool("{name}", arguments)"""

    return body


def generate_method(tool: dict[str, Any]) -> str:
    """Generate complete method code from tool schema.

    Args:
        tool: MCP tool definition

    Returns:
        Complete method code
    """
    name, param_lines, return_type = generate_method_signature(tool)
    docstring = generate_method_docstring(tool)
    body = generate_method_body(tool)

    # Format parameters with proper indentation
    params = ",\n        ".join(param_lines)

    method_code = f"""    async def {name}(
        {params}
    ) -> {return_type}:
        {docstring}
        {body}
"""

    return method_code


async def generate_api_class(server_name: str, server_url: str, tools: list[dict[str, Any]]) -> str:
    """Generate Python API class from MCP tool schemas.

    Args:
        server_name: Name of the MCP server (e.g., 'browser')
        server_url: Base URL of remote MCP server
        tools: List of tool definitions from server

    Returns:
        Python source code for API class
    """
    class_name = snake_to_pascal(server_name) + "API"

    # Start class definition
    class_code = f'''"""Auto-generated API for {server_name} MCP server."""

from __future__ import annotations

from typing import Any, Literal


class {class_name}:
    """Remote MCP: {server_url}

    Auto-generated API from MCP tool schemas.
    """

    def __init__(self, client: Any):
        """Initialize API with MCP client.

        Args:
            client: RemoteMCPClient instance
        """
        self._client = client

'''

    # Generate method for each tool
    for tool in tools:
        class_code += generate_method(tool)
        class_code += "\n"

    return class_code


async def generate_api_from_remote(
    server_name: str, server_url: str, auth_token: str | None = None
) -> str:
    """Generate Python API class from remote MCP server.

    Args:
        server_name: Name to use for the API (e.g., 'browser')
        server_url: Base URL of remote MCP server
        auth_token: Optional authentication token

    Returns:
        Python source code for API class

    Example:
        >>> code = await generate_api_from_remote(
        ...     "browser", "https://browser-mcp.example.com"
        ... )
        >>> # code contains BrowserAPI class with methods for each tool
    """
    from learning_agent.sandbox.remote_mcp_client import RemoteMCPClient

    # Connect to remote server and fetch tools
    client = RemoteMCPClient(server_url, auth_token)
    tools = await client.list_tools()

    # Generate API class
    return await generate_api_class(server_name, server_url, tools)
