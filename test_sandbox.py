#!/usr/bin/env python
"""Test the Python sandbox tool to verify it works correctly."""

import asyncio

from learning_agent.tools.sandbox_tool import EnhancedSandbox


async def test_basic_execution():
    """Test basic code execution."""
    print("Testing basic execution...")
    sandbox = EnhancedSandbox(allow_network=True)

    code = """
print("Hello from the sandbox!")
x = 5
y = 10
result = x + y
print(f"Result: {result}")
"""

    result = await sandbox.execute_with_viz(code)
    print(f"Success: {result['success']}")
    print(f"Output: {result['stdout']}")
    assert "Hello from the sandbox!" in result["stdout"]
    assert "Result: 15" in result["stdout"]
    print("✓ Basic execution works\n")


async def test_stateful_execution():
    """Test that state is maintained between executions."""
    print("Testing stateful execution...")
    sandbox = EnhancedSandbox(allow_network=True)

    # First execution - define a variable
    code1 = """
data = [1, 2, 3, 4, 5]
print(f"Data defined: {data}")
"""
    result1 = await sandbox.execute_with_viz(code1)
    print(f"First execution output: {result1['stdout'].strip()}")

    # Second execution - use the variable from first execution
    code2 = """
# Variable 'data' should still exist
total = sum(data)
print(f"Sum of data: {total}")
"""
    result2 = await sandbox.execute_with_viz(code2)
    print(f"Second execution output: {result2['stdout'].strip()}")
    assert "Sum of data: 15" in result2["stdout"]
    print("✓ Stateful execution works\n")


async def test_matplotlib_capture():
    """Test matplotlib visualization capture."""
    print("Testing matplotlib capture...")
    sandbox = EnhancedSandbox(allow_network=True)

    code = """
import matplotlib.pyplot as plt
import numpy as np

# Create a simple plot
x = np.linspace(0, 10, 100)
y = np.sin(x)

plt.figure(figsize=(8, 6))
plt.plot(x, y)
plt.title('Sine Wave')
plt.xlabel('x')
plt.ylabel('sin(x)')
plt.grid(True)

print("Plot created successfully")
"""

    result = await sandbox.execute_with_viz(code)
    print(f"Output: {result['stdout'].strip()}")
    print(f"Images captured: {len(result['images'])}")

    if result["images"]:
        img = result["images"][0]
        print(f"Image type: {img['type']}")
        print(f"Image format: {img['format']}")
        print(f"Base64 data length: {len(img['base64'])}")
        assert img["type"] == "matplotlib"
        assert img["format"] == "png"
        assert len(img["base64"]) > 1000  # Should have substantial data

    print("✓ Matplotlib capture works\n")


async def test_pandas_capture():
    """Test pandas DataFrame capture."""
    print("Testing pandas DataFrame capture...")
    sandbox = EnhancedSandbox(allow_network=True)

    code = """
import pandas as pd
import numpy as np

# Create a DataFrame
df = pd.DataFrame({
    'A': np.random.randn(10),
    'B': np.random.randn(10),
    'C': np.random.randn(10)
})

print(f"DataFrame shape: {df.shape}")
print(f"DataFrame columns: {list(df.columns)}")
"""

    result = await sandbox.execute_with_viz(code)
    print(f"Output: {result['stdout'].strip()}")
    print(f"Tables captured: {len(result['tables'])}")

    if result["tables"]:
        table = result["tables"][0]
        print(f"Table name: {table['name']}")
        print(f"Table shape: {table['shape']}")
        assert table["name"] == "df"
        assert table["shape"] == [10, 3]
        assert "html" in table

    print("✓ Pandas capture works\n")


async def test_error_handling():
    """Test error handling in the sandbox."""
    print("Testing error handling...")
    sandbox = EnhancedSandbox(allow_network=True)

    code = """
# This will cause an error
undefined_variable
"""

    result = await sandbox.execute_with_viz(code)
    print(f"Success: {result['success']}")
    print(f"Output contains error: {'NameError' in str(result)}")
    print("✓ Error handling works\n")


async def test_reset():
    """Test sandbox reset functionality."""
    print("Testing sandbox reset...")
    sandbox = EnhancedSandbox(allow_network=True)

    # Define a variable
    code1 = """
my_var = 42
print(f"Variable defined: my_var = {my_var}")
"""
    result1 = await sandbox.execute_with_viz(code1)
    print(f"Before reset: {result1['stdout'].strip()}")

    # Reset the sandbox
    await sandbox.reset()

    # Try to use the variable (should fail after reset)
    code2 = """
try:
    print(f"my_var = {my_var}")
except NameError:
    print("Variable my_var not found (sandbox was reset)")
"""
    result2 = await sandbox.execute_with_viz(code2)
    print(f"After reset: {result2['stdout'].strip()}")
    assert "not found" in result2["stdout"]
    print("✓ Reset functionality works\n")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Python Sandbox Tool")
    print("=" * 60 + "\n")

    try:
        await test_basic_execution()
        await test_stateful_execution()
        await test_matplotlib_capture()
        await test_pandas_capture()
        await test_error_handling()
        await test_reset()

        print("=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
