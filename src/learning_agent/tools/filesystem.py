"""Filesystem tool for file operations."""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import aiofiles
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class FilesystemInput(BaseModel):
    """Input for filesystem operations."""

    action: str = Field(
        description="Action: read, write, append, delete, create_dir, list_dir, search, move, copy"
    )
    path: str = Field(description="File or directory path")
    content: str | None = Field(None, description="Content for write/append operations")
    pattern: str | None = Field(None, description="Search pattern for search operation")
    destination: str | None = Field(None, description="Destination path for move/copy")
    encoding: str = Field("utf-8", description="File encoding")


class FilesystemTool(BaseTool):  # type: ignore[misc]
    """Tool for filesystem operations."""

    name: str = "filesystem_tool"
    description: str = "Perform filesystem operations: read, write, delete files and directories"
    args_schema: type[BaseModel] = FilesystemInput

    def __init__(self, base_path: Path | None = None):
        """Initialize filesystem tool."""
        super().__init__()
        self._base_path = base_path or Path.cwd()
        self._operation_history: list[dict[str, Any]] = []

    @property
    def base_path(self) -> Path:
        return self._base_path

    @property
    def operation_history(self) -> list[dict[str, Any]]:
        return self._operation_history

    def _run(
        self,
        action: str,
        path: str,
        content: str | None = None,
        pattern: str | None = None,
        destination: str | None = None,
        encoding: str = "utf-8",
        **kwargs: Any,  # noqa: ARG002
    ) -> str:
        """Execute filesystem operation."""
        # Resolve path relative to base
        full_path = self._resolve_path(path)

        try:
            if action == "read":
                return self._read_file(full_path, encoding)
            if action == "write":
                return self._write_file(full_path, content or "", encoding)
            if action == "append":
                return self._append_file(full_path, content or "", encoding)
            if action == "delete":
                return self._delete(full_path)
            if action == "create_dir":
                return self._create_directory(full_path)
            if action == "list_dir":
                return self._list_directory(full_path)
            if action == "search":
                return self._search_files(full_path, pattern or "*")
            if action == "move":
                dest_path = self._resolve_path(destination) if destination else None
                return self._move(full_path, dest_path)
            if action == "copy":
                dest_path = self._resolve_path(destination) if destination else None
                return self._copy(full_path, dest_path)
        except Exception as e:
            error_msg = f"Error performing {action}: {e}"
            self._log_operation(action, path, success=False, error=str(e))
            return error_msg
        else:
            return f"Unknown action: {action}"

    async def _arun(
        self,
        action: str,
        path: str,
        content: str | None = None,
        pattern: str | None = None,
        destination: str | None = None,
        encoding: str = "utf-8",
        **kwargs: Any,
    ) -> str:
        """Async version of filesystem operations."""
        full_path = self._resolve_path(path)

        try:
            if action == "read":
                return await self._async_read_file(full_path, encoding)
            if action == "write":
                return await self._async_write_file(full_path, content or "", encoding)
            if action == "append":
                return await self._async_append_file(full_path, content or "", encoding)
            # Fall back to sync for other operations
            return self._run(action, path, content, pattern, destination, encoding, **kwargs)
        except Exception as e:
            error_msg = f"Error performing {action}: {e}"
            self._log_operation(action, path, success=False, error=str(e))
            return error_msg

    def _resolve_path(self, path: str) -> Path:
        """Resolve path relative to base path."""
        p = Path(path)
        if p.is_absolute():
            return p
        return self.base_path / p

    def _read_file(self, path: Path, encoding: str) -> str:
        """Read file contents."""
        if not path.exists():
            return f"File not found: {path}"

        if not path.is_file():
            return f"Not a file: {path}"

        content = path.read_text(encoding=encoding)
        self._log_operation("read", str(path), success=True, size=len(content))
        return str(content)

    async def _async_read_file(self, path: Path, encoding: str) -> str:
        """Async read file contents."""
        if not path.exists():
            return f"File not found: {path}"

        if not path.is_file():
            return f"Not a file: {path}"

        async with aiofiles.open(path, encoding=encoding) as f:
            content = await f.read()

        self._log_operation("read", str(path), success=True, size=len(content))
        return str(content)

    def _write_file(self, path: Path, content: str, encoding: str) -> str:
        """Write content to file."""
        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write with atomic operation (write to temp, then rename)
        temp_path = path.with_suffix(path.suffix + ".tmp")
        temp_path.write_text(content, encoding=encoding)
        temp_path.replace(path)

        self._log_operation("write", str(path), success=True, size=len(content))
        return f"Wrote {len(content)} bytes to {path}"

    async def _async_write_file(self, path: Path, content: str, encoding: str) -> str:
        """Async write content to file."""
        path.parent.mkdir(parents=True, exist_ok=True)

        temp_path = path.with_suffix(path.suffix + ".tmp")
        async with aiofiles.open(temp_path, mode="w", encoding=encoding) as f:
            await f.write(content)

        temp_path.replace(path)

        self._log_operation("write", str(path), success=True, size=len(content))
        return f"Wrote {len(content)} bytes to {path}"

    def _append_file(self, path: Path, content: str, encoding: str) -> str:
        """Append content to file."""
        if not path.exists():
            return self._write_file(path, content, encoding)

        with path.open("a", encoding=encoding) as f:
            f.write(content)

        self._log_operation("append", str(path), success=True, size=len(content))
        return f"Appended {len(content)} bytes to {path}"

    async def _async_append_file(self, path: Path, content: str, encoding: str) -> str:
        """Async append content to file."""
        if not path.exists():
            return await self._async_write_file(path, content, encoding)

        async with aiofiles.open(path, mode="a", encoding=encoding) as f:
            await f.write(content)

        self._log_operation("append", str(path), success=True, size=len(content))
        return f"Appended {len(content)} bytes to {path}"

    def _delete(self, path: Path) -> str:
        """Delete file or directory."""
        if not path.exists():
            return f"Path not found: {path}"

        if path.is_file():
            path.unlink()
            self._log_operation("delete", str(path), success=True, type="file")
            return f"Deleted file: {path}"
        if path.is_dir():
            shutil.rmtree(path)
            self._log_operation("delete", str(path), success=True, type="directory")
            return f"Deleted directory: {path}"
        return f"Unknown path type: {path}"

    def _create_directory(self, path: Path) -> str:
        """Create directory."""
        path.mkdir(parents=True, exist_ok=True)
        self._log_operation("create_dir", str(path), success=True)
        return f"Created directory: {path}"

    def _list_directory(self, path: Path) -> str:
        """List directory contents."""
        if not path.exists():
            return f"Directory not found: {path}"

        if not path.is_dir():
            return f"Not a directory: {path}"

        items = []
        for item in sorted(path.iterdir()):
            if item.is_file():
                size = item.stat().st_size
                items.append(f"📄 {item.name} ({size} bytes)")
            elif item.is_dir():
                items.append(f"📁 {item.name}/")
            else:
                items.append(f"❓ {item.name}")

        if not items:
            return f"Empty directory: {path}"

        self._log_operation("list_dir", str(path), success=True, count=len(items))
        return f"Contents of {path}:\n" + "\n".join(items)

    def _search_files(self, path: Path, pattern: str) -> str:
        """Search for files matching pattern."""
        if not path.exists():
            return f"Path not found: {path}"

        matches = []
        if path.is_file():
            # Search in single file
            if pattern.lower() in path.name.lower():
                matches.append(str(path))
        else:
            # Search in directory
            matches.extend(str(item) for item in path.rglob(pattern))

        if not matches:
            return f"No files matching '{pattern}' found in {path}"

        self._log_operation(
            "search", str(path), success=True, pattern=pattern, matches=len(matches)
        )
        return f"Found {len(matches)} matches:\n" + "\n".join(matches[:20])  # Limit to 20 results

    def _move(self, source: Path, destination: Path | None) -> str:
        """Move file or directory."""
        if not source.exists():
            return f"Source not found: {source}"

        if destination is None:
            return "Destination path required for move operation"

        # If destination is a directory, preserve filename
        if destination.is_dir():
            destination = destination / source.name

        # Create parent directories if needed
        destination.parent.mkdir(parents=True, exist_ok=True)

        shutil.move(str(source), str(destination))

        self._log_operation("move", str(source), success=True, destination=str(destination))
        return f"Moved {source} to {destination}"

    def _copy(self, source: Path, destination: Path | None) -> str:
        """Copy file or directory."""
        if not source.exists():
            return f"Source not found: {source}"

        if destination is None:
            return "Destination path required for copy operation"

        # If destination is a directory, preserve filename
        if destination.is_dir():
            destination = destination / source.name

        # Create parent directories if needed
        destination.parent.mkdir(parents=True, exist_ok=True)

        if source.is_file():
            shutil.copy2(str(source), str(destination))
        else:
            shutil.copytree(str(source), str(destination))

        self._log_operation("copy", str(source), success=True, destination=str(destination))
        return f"Copied {source} to {destination}"

    def _log_operation(self, action: str, path: str, success: bool, **kwargs: Any) -> None:
        """Log filesystem operation."""
        log_entry = {
            "action": action,
            "path": path,
            "success": success,
            "timestamp": datetime.now().isoformat(),
            **kwargs,
        }
        self.operation_history.append(log_entry)

    def get_history(self) -> list[dict[str, Any]]:
        """Get operation history."""
        return self.operation_history

    def clear_history(self) -> None:
        """Clear operation history."""
        self.operation_history.clear()
