# IMPORTANT: langchain-sandbox Installation & TypeScript Source

## Critical Information
The `langchain-sandbox` package MUST be installed from the GitHub repository, NOT from PyPI.

### Why?
The official PyPI package (`langchain-sandbox==0.0.1`) lacks:
- TypeScript/JavaScript execution support
- Matplotlib fixes for Pyodide environments
- Proper error handling for import detection

### Correct Installation

#### From GitHub (CORRECT ✅):
```bash
pip install git+https://github.com/johannhartmann/langchain-sandbox.git@main#subdirectory=libs/sandbox-py
```

Or use the Makefile:
```bash
make install-sandbox
```

#### From PyPI (WRONG ❌):
```bash
# DO NOT DO THIS!
pip install langchain-sandbox  # This installs the broken 0.0.1 version
```

### Verification
Check your installation:
```bash
pip show langchain-sandbox
```

- **Good**: Version 0.0.6+ from GitHub
- **Bad**: Version 0.0.1 from PyPI

### Enforcement
This project has safeguards to prevent incorrect installation:

1. **pyproject.toml**: Specifies GitHub source with git URL
2. **constraints.txt**: Forces pip to use GitHub source
3. **requirements-sandbox.txt**: Explicit GitHub URL for standalone installs
4. **Dockerfile**: Includes verification step that fails if PyPI version detected
5. **Makefile**: `make install-sandbox` command for correct installation

### TypeScript/Deno Source
The sandbox uses Deno to execute TypeScript code that runs Pyodide. This TypeScript code MUST be loaded from GitHub, not from JSR (JavaScript Registry).

#### Why Avoid JSR?
- JSR packages may have different dependencies
- Our GitHub version has specific fixes for matplotlib and imports
- Direct Deno.land URLs ensure consistent behavior

#### Automatic Protection
The project automatically:
1. Downloads TypeScript source from GitHub
2. Replaces `@std/` imports with `https://deno.land/std@` URLs
3. Patches PyodideSandbox to use the GitHub source
4. Sets environment variables to prevent JSR usage

### Verification
Run this command to verify everything is correctly configured:
```bash
make verify-sandbox
```

Expected output:
```
✓ langchain-sandbox version: 0.0.7+
✓ TypeScript source configured: /tmp/langchain-sandbox-ts/pyodide_sandbox.ts
✓ TypeScript source uses direct Deno.land URLs (no JSR)
✓ PyodideSandbox using: /tmp/langchain-sandbox-ts/pyodide_sandbox.ts
============================================================
VERIFICATION PASSED
✅ All sandbox sources are correctly configured from GitHub
```

### If You See Sandbox Errors
If you encounter errors like:
- "ModuleNotFoundError: No module named 'matplotlib.pyplot'"
- TypeScript/JavaScript execution failures
- Matplotlib visualization issues
- JSR package errors

Run:
```bash
make install-sandbox
make verify-sandbox
```

This will:
1. Uninstall any incorrect version
2. Install from GitHub
3. Configure TypeScript source correctly
4. Verify the installation
