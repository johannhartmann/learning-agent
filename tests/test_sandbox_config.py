#!/usr/bin/env python3
"""Test that sandbox configuration prevents JSR usage."""

import os
import tempfile
from pathlib import Path

import pytest

from learning_agent.tools.sandbox_config import (
    create_deno_import_map,
    ensure_github_typescript_source,
    patch_pyodide_sandbox,
)


class TestSandboxConfiguration:
    """Test sandbox configuration to ensure GitHub sources are used."""

    def test_typescript_source_no_jsr(self):
        """Verify TypeScript source doesn't use JSR imports."""
        # Get the TypeScript source
        ts_source = ensure_github_typescript_source()

        assert ts_source is not None
        assert ts_source.endswith(".ts") or ts_source.startswith("http")

        # If it's a file, check its contents
        if Path(ts_source).exists():
            content = Path(ts_source).read_text()

            # Should NOT have JSR imports
            assert "jsr:" not in content, "TypeScript should not use JSR imports"
            assert "@std/" not in content or "deno.land/std" in content, (
                "Should use Deno.land URLs, not @std shortcuts"
            )

            # Should have correct imports
            assert "deno.land/std" in content or "npm:pyodide" in content, (
                "Should use Deno.land or npm imports"
            )

    def test_patch_pyodide_sandbox(self):
        """Test that patching PyodideSandbox changes PKG_NAME."""
        from langchain_sandbox import pyodide

        # Store original value
        original_pkg = pyodide.PKG_NAME

        # Apply patch
        patch_pyodide_sandbox()

        # Check it changed
        assert original_pkg != pyodide.PKG_NAME or "jsr:" not in pyodide.PKG_NAME
        assert "jsr:" not in pyodide.PKG_NAME, "Should not use JSR after patching"

        # Should be a file path or GitHub URL
        assert (
            pyodide.PKG_NAME.endswith(".ts")
            or "github" in pyodide.PKG_NAME
            or "/tmp/" in pyodide.PKG_NAME
        ), f"Unexpected package source after patching: {pyodide.PKG_NAME}"

    def test_deno_import_map(self):
        """Test Deno import map generation."""
        import_map = create_deno_import_map()

        assert "imports" in import_map
        imports = import_map["imports"]

        # Check key imports are mapped
        assert "@std/path" in imports
        assert "@std/cli/parse-args" in imports

        # Should map to Deno.land URLs
        assert imports["@std/path"].startswith("https://deno.land/std")
        assert imports["@std/cli/parse-args"].startswith("https://deno.land/std")

        # Should include pyodide
        assert "pyodide" in imports

    def test_environment_variable_override(self):
        """Test that environment variable can override TypeScript source."""
        # Create a temporary TypeScript file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ts", delete=False) as f:
            f.write("// Test TypeScript file\n")
            temp_ts = f.name

        try:
            # Set environment variable
            os.environ["LANGCHAIN_SANDBOX_TS_SOURCE"] = temp_ts

            # Should use the override
            ts_source = ensure_github_typescript_source()
            assert ts_source == temp_ts

        finally:
            # Clean up
            del os.environ["LANGCHAIN_SANDBOX_TS_SOURCE"]
            Path(temp_ts).unlink()

    def test_github_source_download(self):
        """Test downloading TypeScript from GitHub."""
        # Remove cached file if it exists
        cache_file = Path("/tmp/langchain-sandbox-ts/pyodide_sandbox.ts")
        if cache_file.exists():
            cache_file.unlink()

        # Should download from GitHub
        ts_source = ensure_github_typescript_source()

        # Check it was downloaded and processed
        assert Path(ts_source).exists()
        content = Path(ts_source).read_text()

        # Should have replaced imports
        assert "@std/" not in content or "deno.land/std" in content
        assert "npm:pyodide" in content or 'from "pyodide"' not in content

    @pytest.mark.integration
    def test_sandbox_tool_uses_patch(self):
        """Test that importing sandbox_tool applies the patch."""
        # Import should trigger the patch
        from langchain_sandbox import pyodide

        # Check patch was applied
        assert "jsr:" not in pyodide.PKG_NAME, (
            f"Sandbox tool should patch away JSR, but got: {pyodide.PKG_NAME}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
