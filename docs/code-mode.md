# Code-Mode: Remote MCP Integration

## Overview

Code-mode enables the learning agent to use remote MCP (Model Context Protocol) servers by automatically generating Python APIs from tool schemas. Instead of making individual JSON tool calls, the agent writes natural Python code that orchestrates multiple operations efficiently.

This implementation follows [Cloudflare's code-mode pattern](https://blog.cloudflare.com/code-mode/) but adapted for Python in Pyodide sandbox instead of TypeScript in V8 Isolates.

## Architecture

```
┌─────────────┐
│   Agent     │ Writes Python code using mcp.server APIs
└──────┬──────┘
       │
       ▼
┌─────────────────────────────┐
│  Pyodide Sandbox            │
│  ┌───────────────────────┐  │
│  │ # Auto-injected       │  │
│  │ browser = mcp.browser │  │
│  │ browser.goto(url)     │  │
│  └───────────────────────┘  │
└──────────┬──────────────────┘
           │
           ▼
┌──────────────────────┐
│  MCP HTTP Bridge     │ Validates & proxies requests
└──────────┬───────────┘
           │
           ▼
┌───────────────────────────┐
│  Remote MCP Server        │
│  https://api.example.com  │
│  ┌─────────────────────┐  │
│  │ Tools:              │  │
│  │ - goto()            │  │
│  │ - screenshot()      │  │
│  │ - extract_data()    │  │
│  └─────────────────────┘  │
└───────────────────────────┘
```

## Configuration

### 1. Add Remote MCP Server to Configuration

Edit `mcp_servers.json` in the project root:

```json
{
  "servers": {
    "github": {
      "url": "https://api.githubcopilot.com/mcp",
      "type": "remote-https",
      "description": "GitHub Copilot MCP server",
      "auth": {
        "type": "bearer",
        "token_env": "GITHUB_COPILOT_TOKEN"
      },
      "enabled": true
    }
  }
}
```

### Configuration Options

| Field | Required | Description |
|-------|----------|-------------|
| `url` | Yes | Base URL of the remote MCP server (must be HTTPS) |
| `type` | Yes | Must be `"remote-https"` |
| `description` | No | Human-readable description of the server |
| `auth.type` | No | Authentication type: `"bearer"` or omit for no auth |
| `auth.token_env` | No | Environment variable containing Bearer token |
| `auth.token` | No | Direct token (not recommended for production) |
| `enabled` | Yes | Set to `true` to enable this server |

### 2. Set Authentication Token

If the MCP server requires authentication, set the environment variable:

```bash
export GITHUB_COPILOT_TOKEN="your-token-here"
```

Or add to `.env` file:

```bash
GITHUB_COPILOT_TOKEN=your-token-here
```

### 3. Initialize Sandbox with MCP Support

The sandbox automatically loads configured MCP servers on initialization. No additional setup required.

## Usage in Agent Code

### Basic Example

Once configured, the agent can write Python code using the auto-generated API:

```python
# Agent writes this code in python_sandbox tool
browser = mcp.github  # Auto-generated API from remote server

# Type-safe Python methods (not JSON tool calls)
result = browser.search_repositories(
    query="machine learning",
    language="python",
    stars=">1000"
)

print(f"Found {len(result['items'])} repositories")
for repo in result['items'][:5]:
    print(f"- {repo['name']}: {repo['description']}")
```

### Complex Workflows

Code-mode enables sophisticated multi-step workflows:

```python
github = mcp.github

# Search for repositories
repos = github.search_repositories(
    query="langchain",
    sort="stars",
    order="desc"
)

# Analyze each top repository
analysis = []
for repo in repos['items'][:3]:
    # Get repository details
    details = github.get_repository(
        owner=repo['owner']['login'],
        name=repo['name']
    )

    # Get recent issues
    issues = github.list_issues(
        owner=repo['owner']['login'],
        name=repo['name'],
        state="open",
        per_page=5
    )

    analysis.append({
        'name': repo['name'],
        'stars': details['stargazers_count'],
        'open_issues': len(issues),
        'topics': details.get('topics', [])
    })

print(json.dumps(analysis, indent=2))
```

### Error Handling

Use Python try/except for robust error handling:

```python
github = mcp.github

try:
    result = github.get_user("nonexistent-user-12345")
except Exception as e:
    print(f"User not found: {e}")
    # Fallback behavior
    result = github.search_users("similar-name")
```

## API Generation

### How It Works

1. **Schema Retrieval**: When sandbox initializes, it fetches tool schemas from the remote MCP server via `GET /tools/list`

2. **Type Generation**: JSON Schema types are converted to Python type hints:
   - `string` → `str`
   - `integer` → `int`
   - `number` → `float`
   - `boolean` → `bool`
   - `array` → `list[T]`
   - `object` → `dict[str, Any]`
   - `enum` → `Literal["a", "b", "c"]`

3. **Method Generation**: Each tool becomes a Python async method with:
   - Type-safe parameters
   - Docstrings from tool descriptions
   - Automatic argument validation

4. **API Injection**: The generated API is injected into sandbox globals as `mcp.server_name`

### Example: Tool Schema → Python API

**MCP Tool Schema** (from `GET /tools/list`):
```json
{
  "name": "search_repositories",
  "description": "Search for GitHub repositories",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Search query"
      },
      "language": {
        "type": "string",
        "description": "Programming language filter"
      },
      "stars": {
        "type": "string",
        "description": "Star count filter (e.g., '>1000')"
      },
      "sort": {
        "type": "string",
        "enum": ["stars", "forks", "updated"],
        "description": "Sort order"
      }
    },
    "required": ["query"]
  }
}
```

**Generated Python API**:
```python
class GithubAPI:
    """Remote MCP: https://api.githubcopilot.com/mcp"""

    async def search_repositories(
        self,
        query: str,
        language: str | None = None,
        stars: str | None = None,
        sort: Literal["stars", "forks", "updated"] | None = None
    ) -> dict[str, Any]:
        """Search for GitHub repositories

        Args:
            query: Search query
            language: Programming language filter
            stars: Star count filter (e.g., '>1000')
            sort: Sort order

        Returns:
            Tool execution result
        """
        arguments = {
            "query": query,
            "language": language,
            "stars": stars,
            "sort": sort
        }
        # Remove None values
        arguments = {k: v for k, v in arguments.items() if v is not None}
        return await self._client.call_tool("search_repositories", arguments)
```

## Agent Prompt Integration

The agent's system prompt automatically includes code-mode examples when MCP servers are configured:

```
## Code-Mode with Remote MCP Servers

You can use remote MCP tools via Python code in the `python_sandbox`.
Available servers: github

Example:
python_sandbox('''
github = mcp.github
repos = github.search_repositories(query="AI agents")
for repo in repos['items'][:5]:
    print(f"{repo['name']}: {repo['stargazers_count']} stars")
''')
```

## Benefits of Code-Mode

### 1. Natural Python Instead of JSON

**Before (Direct Tool Calls):**
```
Agent: [calls github_search with {"query": "AI"}]
Agent: [calls github_get_repo with {"owner": "...", "name": "..."}]
Agent: [calls github_list_issues with {"owner": "...", "name": "..."}]
```

**After (Code-Mode):**
```python
github = mcp.github
repos = github.search_repositories(query="AI")
for repo in repos['items'][:3]:
    details = github.get_repository(owner=repo['owner'], name=repo['name'])
    issues = github.list_issues(owner=repo['owner'], name=repo['name'])
    print(f"{repo['name']}: {len(issues)} open issues")
```

### 2. Better Token Efficiency

- Fewer messages in conversation history
- Compact Python loops vs repeated tool calls
- LLM's coding ability vs tool selection

### 3. More Expressive

- Loops, conditionals, error handling
- Local variables and data transformation
- Complex multi-step logic in single execution

### 4. Type Safety

- Auto-generated type hints prevent errors
- IDE-like experience for the LLM
- Clear parameter requirements

## Security

### Sandbox Isolation

- Code executes in Pyodide sandbox with restricted permissions
- No file system access outside designated paths
- Network limited to MCP server communication only

### Server Validation

- Only servers in `mcp_servers.json` are allowed
- HTTP bridge validates all requests
- Bearer tokens from environment variables (not hardcoded)

### Authentication

- Bearer tokens never exposed to sandbox code
- HTTP bridge handles authentication transparently
- Tokens read from environment variables at runtime

## Troubleshooting

### MCP Server Not Loading

**Problem**: Agent cannot access `mcp.server_name`

**Solutions**:
1. Check `mcp_servers.json` has `"enabled": true`
2. Verify `url` is correct and accessible
3. Check authentication token if required
4. Review logs for connection errors

### Authentication Errors

**Problem**: HTTP 401 Unauthorized

**Solutions**:
1. Verify token environment variable is set: `echo $GITHUB_COPILOT_TOKEN`
2. Check token has not expired
3. Confirm `auth.token_env` matches actual env var name

### Type Errors in Generated API

**Problem**: Method signatures don't match expected usage

**Solutions**:
1. Check MCP server's tool schema with: `curl -H "Authorization: Bearer $TOKEN" https://api.example.com/mcp/tools/list`
2. Clear sandbox cache and reinitialize
3. Report issue with tool schema for investigation

### Timeout Errors

**Problem**: Requests to MCP server timeout

**Solutions**:
1. Default timeout is 30 seconds - check if server is slow
2. Verify network connectivity to remote server
3. Check for rate limiting on MCP server

## Testing

### Mock MCP Server for Testing

Create a mock server for testing without a real MCP endpoint:

```python
# tests/test_code_mode_integration.py
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_code_mode_with_mock_server():
    """Test code-mode with mocked MCP server."""
    from learning_agent.tools.sandbox_tool import EnhancedSandbox

    # Mock MCP server configuration
    mcp_config = {
        "test-server": {
            "url": "https://test.example.com",
            "enabled": True
        }
    }

    # Mock the HTTP responses
    mock_tools = [
        {
            "name": "echo",
            "description": "Echo back input",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "message": {"type": "string"}
                },
                "required": ["message"]
            }
        }
    ]

    with patch('learning_agent.sandbox.mcp_http_bridge.MCPHttpBridge.list_tools') as mock_list:
        mock_list.return_value = mock_tools

        # Create sandbox with MCP support
        sandbox = EnhancedSandbox(
            allow_network=True,
            mcp_servers=mcp_config
        )

        # Execute code using MCP API
        result = await sandbox.execute_with_viz('''
test_server = mcp.test_server
result = test_server.echo(message="Hello, MCP!")
print(result)
''')

        assert result['success']
        assert "Hello, MCP!" in result['stdout']
```

### Integration Test with Real Server

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_mcp_server():
    """Test with actual remote MCP server (requires credentials)."""
    import os

    # Skip if no credentials
    if not os.getenv('GITHUB_COPILOT_TOKEN'):
        pytest.skip("GITHUB_COPILOT_TOKEN not set")

    from learning_agent.tools.sandbox_tool import EnhancedSandbox

    mcp_config = {
        "github": {
            "url": "https://api.githubcopilot.com/mcp",
            "auth": {
                "type": "bearer",
                "token_env": "GITHUB_COPILOT_TOKEN"
            },
            "enabled": True
        }
    }

    sandbox = EnhancedSandbox(
        allow_network=True,
        mcp_servers=mcp_config
    )

    result = await sandbox.execute_with_viz('''
github = mcp.github
# Simple API call to verify connectivity
user = github.get_user("torvalds")
print(f"User: {user['name']}")
print(f"Followers: {user['followers']}")
''')

    assert result['success']
    assert "User:" in result['stdout']
```

## Advanced Usage

### Multiple MCP Servers

Configure and use multiple servers simultaneously:

```json
{
  "servers": {
    "github": {
      "url": "https://api.githubcopilot.com/mcp",
      "auth": {"type": "bearer", "token_env": "GITHUB_TOKEN"},
      "enabled": true
    },
    "browser": {
      "url": "https://browser-mcp.example.com",
      "auth": {"type": "bearer", "token_env": "BROWSER_TOKEN"},
      "enabled": true
    }
  }
}
```

```python
# Use multiple servers in one workflow
github = mcp.github
browser = mcp.browser

# Search GitHub
repos = github.search_repositories(query="web automation")

# Visit top repo's homepage
top_repo = repos['items'][0]
browser.goto(top_repo['html_url'])
screenshot = browser.screenshot()

print(f"Visited {top_repo['name']} and captured screenshot")
```

### Dynamic Server Discovery

List available servers at runtime:

```python
# Check what MCP servers are available
servers = mcp.list_servers()
print(f"Available MCP servers: {servers}")

# Conditionally use servers
if 'github' in servers:
    github = mcp.github
    # ... use GitHub API
```

## Performance Considerations

### Token Efficiency

Code-mode significantly reduces token usage:

- **Direct tools**: 5-10 tool calls × 500 tokens = 2,500-5,000 tokens
- **Code-mode**: 1 sandbox call × 200 tokens = 200 tokens

### Latency

- **Single HTTP roundtrip** to remote MCP server per method call
- **Parallel execution** possible with asyncio in sandbox
- **Connection pooling** managed by HTTP bridge

### Caching

- API schemas cached after first load
- No re-fetching on subsequent sandbox executions
- Clear cache by restarting agent

## References

- [Cloudflare Code-Mode Blog Post](https://blog.cloudflare.com/code-mode/)
- [MCP Specification](https://modelcontextprotocol.io/specification/2025-06-18)
- [MCP Tools Specification](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)
- [MCP Resources Specification](https://modelcontextprotocol.io/specification/2025-06-18/server/resources)

## Support

For issues or questions about code-mode:

1. Check logs: `docker compose logs server`
2. Verify MCP server connectivity: `curl -H "Authorization: Bearer $TOKEN" https://api.example.com/mcp/tools/list`
3. Review sandbox execution errors in agent output
4. File issue with full error logs and MCP server configuration
