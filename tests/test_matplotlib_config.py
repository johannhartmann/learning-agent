#!/usr/bin/env python3
"""Lightweight tests for matplotlib configuration in Docker environment."""

import os
import subprocess
from pathlib import Path

import pytest


class TestMatplotlibConfiguration:
    """Test matplotlib/sandbox configuration without full execution."""

    def test_langchain_sandbox_version(self):
        """Verify langchain-sandbox is from GitHub, not PyPI."""
        import langchain_sandbox

        version = getattr(langchain_sandbox, "__version__", "unknown")
        print(f"langchain-sandbox version: {version}")

        # Should NOT be the PyPI version
        assert version != "0.0.1", "Should not be using PyPI version 0.0.1"

        # Should be 0.0.6+ or unknown (from GitHub)
        assert version in ["unknown", "0.0.6", "0.0.7"] or version > "0.0.6", (
            f"Unexpected version: {version}"
        )

    def test_sandbox_tool_import(self):
        """Test that sandbox tool can be imported and configured."""
        from learning_agent.tools.sandbox_tool import create_sandbox_tool, python_sandbox

        # Should be able to create the tool
        tool = create_sandbox_tool()
        assert tool is not None
        assert tool == python_sandbox

        # Check tool metadata
        assert hasattr(tool, "name")
        assert tool.name == "python_sandbox"
        assert hasattr(tool, "description")
        assert "Python" in tool.description

    def test_pyodide_pkg_name(self):
        """Verify PyodideSandbox is not using JSR."""
        from langchain_sandbox import pyodide

        pkg_name = pyodide.PKG_NAME
        print(f"PyodideSandbox PKG_NAME: {pkg_name}")

        # Should NOT use JSR
        assert "jsr:" not in pkg_name, f"Should not use JSR, got: {pkg_name}"

        # Should be a file or URL
        assert pkg_name.endswith(".ts") or pkg_name.startswith("http"), (
            f"Unexpected package source: {pkg_name}"
        )

    @pytest.mark.docker
    def test_docker_environment_variables(self):
        """Test Docker environment is configured correctly."""
        if not Path("/.dockerenv").exists():
            pytest.skip("Not running in Docker")

        # Check TypeScript source environment variable
        ts_source = os.environ.get("LANGCHAIN_SANDBOX_TS_SOURCE")
        assert ts_source is not None, "LANGCHAIN_SANDBOX_TS_SOURCE not set in Docker"
        assert ts_source == "/tmp/langchain-sandbox-ts/pyodide_sandbox.ts"

        # Verify the file exists
        assert Path(ts_source).exists(), f"TypeScript source not found: {ts_source}"

        # Check its contents
        content = Path(ts_source).read_text()
        assert "jsr:" not in content, "Docker TypeScript should not use JSR"
        assert "deno.land/std" in content, "Should use Deno.land URLs"
        assert "npm:pyodide" in content, "Should use npm for pyodide"

    def test_agent_has_sandbox_tool(self):
        """Test that the agent includes the sandbox tool."""
        from learning_agent.tools.sandbox_tool import create_sandbox_tool

        # Just verify the tool can be created
        tool = create_sandbox_tool()
        assert tool is not None
        assert tool.name == "python_sandbox"

        # Verify it's imported in the agent module
        from learning_agent import agent

        # Check that the agent module imports the sandbox tool
        assert "create_sandbox_tool" in dir(agent)

    def test_error_feedback_in_state(self):
        """Test that state includes sandbox error history field."""
        from learning_agent.state import LearningAgentState

        # Check the state has the error history field
        state_annotations = LearningAgentState.__annotations__
        assert "sandbox_error_history" in state_annotations, (
            "State should have sandbox_error_history field"
        )

    @pytest.mark.integration
    def test_docker_compose_config(self):
        """Test Docker Compose configuration is correct."""
        import os

        # Skip this test when running in Docker (files not copied)
        if os.environ.get("DOCKER_ENV"):
            pytest.skip("Skipping Docker config test when running in Docker container")

        # Check docker-compose.yml exists
        compose_file = Path(__file__).parent.parent / "docker-compose.yml"
        assert compose_file.exists(), "docker-compose.yml should exist"

        # Check Dockerfile.server exists
        dockerfile = Path(__file__).parent.parent / "Dockerfile.server"
        assert dockerfile.exists(), "Dockerfile.server should exist"

        # Verify Dockerfile has our checks
        dockerfile_content = dockerfile.read_text()
        assert "langchain-sandbox" in dockerfile_content
        assert "TypeScript source prepared from GitHub" in dockerfile_content
        assert "LANGCHAIN_SANDBOX_TS_SOURCE" in dockerfile_content


def run_in_docker():
    """Run tests in Docker environment."""
    result = subprocess.run(
        [
            "docker-compose",
            "run",
            "--rm",
            "-e",
            "PYTHONPATH=/app/src",
            "server",
            "python",
            "-m",
            "pytest",
            "tests/test_matplotlib_config.py",
            "-v",
            "-m",
            "docker",
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    return result.returncode == 0


if __name__ == "__main__":
    # Run all tests locally
    import sys

    if Path("/.dockerenv").exists():
        # In Docker, run all tests
        pytest.main([__file__, "-v", "-s"])
    else:
        # Not in Docker, run non-Docker tests
        print("Running local tests...")
        result = pytest.main([__file__, "-v", "-s", "-m", "not docker"])

        if result == 0:
            print("\nLocal tests passed. To run Docker tests, use:")
            print("  docker-compose run --rm server python tests/test_matplotlib_config.py")

        sys.exit(result)
