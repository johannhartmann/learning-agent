#!/usr/bin/env python3
"""Verify that langchain-sandbox is using the correct source."""

import os
import sys
from pathlib import Path


def verify_sandbox_installation() -> bool:
    """Verify langchain-sandbox is installed from GitHub, not PyPI."""
    errors = []

    # Check Python package version
    try:
        import langchain_sandbox

        version = getattr(langchain_sandbox, "__version__", "unknown")
        print(f"✓ langchain-sandbox version: {version}")

        if version == "0.0.1":
            errors.append("ERROR: langchain-sandbox v0.0.1 is from PyPI, not GitHub!")
            errors.append("  The PyPI version lacks TypeScript support and matplotlib fixes.")
            errors.append("  Run: make install-sandbox")

    except ImportError:
        errors.append("ERROR: langchain-sandbox is not installed!")
        errors.append("  Run: make install-sandbox")

    # Check TypeScript source configuration
    ts_source = os.environ.get("LANGCHAIN_SANDBOX_TS_SOURCE")
    if ts_source:
        print(f"✓ TypeScript source configured: {ts_source}")
        if Path(ts_source).exists():
            # Check for JSR imports
            content = Path(ts_source).read_text()
            if "jsr:" in content:
                errors.append("WARNING: TypeScript source contains JSR imports!")
                errors.append("  This may cause dependency issues.")
            elif "@std/" in content and "deno.land" not in content:
                errors.append(
                    "WARNING: TypeScript source uses @std imports without deno.land URLs!"
                )
                errors.append("  This will default to JSR.")
            else:
                print("✓ TypeScript source uses direct Deno.land URLs (no JSR)")
        else:
            errors.append(f"WARNING: Configured TypeScript source does not exist: {ts_source}")
    else:
        print("INFO: TypeScript source not explicitly configured (will use default)")

    # Check if pyodide module is accessible
    try:
        from langchain_sandbox import pyodide

        pkg_name = pyodide.PKG_NAME
        print(f"✓ PyodideSandbox using: {pkg_name}")

        if "jsr:" in pkg_name:
            errors.append("ERROR: PyodideSandbox is using JSR package!")
            errors.append("  This should use the GitHub TypeScript source.")
            errors.append("  Run: make install-sandbox")

    except Exception as e:
        errors.append(f"WARNING: Could not check PyodideSandbox configuration: {e}")

    # Report results
    print("\n" + "=" * 60)
    if errors:
        print("VERIFICATION FAILED\n")
        for error in errors:
            print(error)
        print("\nTo fix these issues:")
        print("1. Run: make install-sandbox")
        print("2. Rebuild Docker: docker-compose build")
        return False
    print("VERIFICATION PASSED")
    print("✅ All sandbox sources are correctly configured from GitHub")
    return True


if __name__ == "__main__":
    success = verify_sandbox_installation()
    sys.exit(0 if success else 1)
