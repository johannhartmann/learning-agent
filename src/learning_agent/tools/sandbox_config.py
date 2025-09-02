"""Custom configuration for PyodideSandbox to ensure GitHub source is used."""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any


# Environment variable to override the TypeScript source location
SANDBOX_TS_SOURCE_ENV = "LANGCHAIN_SANDBOX_TS_SOURCE"

# GitHub source URL for the TypeScript implementation
GITHUB_TS_SOURCE = "https://raw.githubusercontent.com/johannhartmann/langchain-sandbox/main/libs/pyodide-sandbox-js/main.ts"


def ensure_github_typescript_source() -> str:
    """
    Ensure the TypeScript source is from GitHub, not JSR.

    Returns the path to the TypeScript file or the GitHub URL.
    """
    # Check if we have an override path
    override_path = os.environ.get(SANDBOX_TS_SOURCE_ENV)
    if override_path and Path(override_path).exists():
        return override_path

    # Try to use the embedded TypeScript file if it exists
    embedded_ts = Path(__file__).parent.parent.parent / "langchain_sandbox" / "pyodide_sandbox.ts"
    if embedded_ts.exists():
        # Check if it has JSR imports and replace them
        content = embedded_ts.read_text()
        if "@std/" in content:
            # Replace @std imports with direct Deno.land URLs
            content = content.replace(
                'import { join } from "@std/path";',
                'import { join } from "https://deno.land/std@0.224.0/path/mod.ts";',
            )
            content = content.replace(
                'import { parseArgs } from "@std/cli/parse-args";',
                'import { parseArgs } from "https://deno.land/std@0.224.0/cli/parse_args.ts";',
            )
            # Fix pyodide import
            content = content.replace(
                'import { loadPyodide } from "pyodide";',
                'import { loadPyodide } from "npm:pyodide@0.26.4";',
            )

            # Write to a temporary file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".ts", delete=False) as f:
                f.write(content)
                return f.name
        return str(embedded_ts)

    # Download from GitHub if not available locally
    temp_dir = Path(tempfile.gettempdir()) / "langchain-sandbox-ts"
    temp_dir.mkdir(exist_ok=True)

    ts_file = temp_dir / "pyodide_sandbox.ts"

    # Download the file if it doesn't exist or is older than 1 day
    if not ts_file.exists() or (ts_file.stat().st_mtime < (Path(__file__).stat().st_mtime - 86400)):
        try:
            result = subprocess.run(
                ["curl", "-s", "-o", str(ts_file), GITHUB_TS_SOURCE],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and ts_file.exists():
                # Replace JSR imports with Deno.land URLs
                content = ts_file.read_text()
                content = content.replace(
                    'import { join } from "@std/path";',
                    'import { join } from "https://deno.land/std@0.224.0/path/mod.ts";',
                )
                content = content.replace(
                    'import { parseArgs } from "@std/cli/parse-args";',
                    'import { parseArgs } from "https://deno.land/std@0.224.0/cli/parse_args.ts";',
                )
                # Fix pyodide import
                content = content.replace(
                    'import { loadPyodide } from "pyodide";',
                    'import { loadPyodide } from "npm:pyodide@0.26.4";',
                )
                ts_file.write_text(content)
                return str(ts_file)
        except Exception as e:
            print(f"Warning: Could not download TypeScript source from GitHub: {e}")

    if ts_file.exists():
        return str(ts_file)

    # Last resort: use the GitHub URL directly (requires network access)
    return GITHUB_TS_SOURCE


def create_deno_import_map() -> dict[str, Any]:
    """
    Create a Deno import map to override JSR imports with GitHub sources.
    """
    return {
        "imports": {
            "@std/path": "https://deno.land/std@0.224.0/path/mod.ts",
            "@std/cli/parse-args": "https://deno.land/std@0.224.0/cli/parse_args.ts",
            "@std/cli": "https://deno.land/std@0.224.0/cli/mod.ts",
            "pyodide": "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js",
        }
    }


def patch_pyodide_sandbox() -> None:
    """
    Monkey-patch the PyodideSandbox to use GitHub source instead of JSR.
    """
    try:
        from langchain_sandbox import pyodide

        # Override the PKG_NAME to use our GitHub source
        ts_source = ensure_github_typescript_source()
        pyodide.PKG_NAME = ts_source

        # Set environment variable for child processes
        os.environ[SANDBOX_TS_SOURCE_ENV] = ts_source

        print(f"✅ PyodideSandbox configured to use TypeScript from: {ts_source}")

    except ImportError:
        print("⚠️ langchain-sandbox not installed, skipping TypeScript source configuration")
