"""Basic test to verify pytest setup."""

import pytest


def test_import():
    """Test that the main package can be imported."""
    import learning_agent

    assert hasattr(learning_agent, "__version__")
    assert learning_agent.__version__ == "0.1.0"


def test_addition():
    """Basic arithmetic test to verify pytest is working."""
    assert 1 + 1 == 2


def test_string():
    """Basic string test."""
    message = "Learning Agent"
    assert message.lower() == "learning agent"
    assert len(message) == 14


@pytest.mark.parametrize(
    "input_val,expected",
    [
        (2, 4),
        (3, 9),
        (4, 16),
        (5, 25),
    ],
)
def test_square(input_val, expected):
    """Test parametrized function."""
    assert input_val**2 == expected


class TestBasicClass:
    """Test class grouping related tests."""

    def test_list_operations(self):
        """Test basic list operations."""
        test_list = [1, 2, 3]
        test_list.append(4)
        assert len(test_list) == 4
        assert test_list[-1] == 4

    def test_dict_operations(self):
        """Test basic dict operations."""
        test_dict = {"key": "value"}
        test_dict["new_key"] = "new_value"
        assert len(test_dict) == 2
        assert "new_key" in test_dict
