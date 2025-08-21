# Contributing to Learning Agent

First off, thank you for considering contributing to Learning Agent! It's people like you that make Learning Agent such a great tool.

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible:

* **Use a clear and descriptive title**
* **Describe the exact steps to reproduce the problem**
* **Provide specific examples to demonstrate the steps**
* **Describe the behavior you observed and expected**
* **Include logs and stack traces if available**
* **Include your environment details** (OS, Python version, package versions)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

* **Use a clear and descriptive title**
* **Provide a detailed description of the suggested enhancement**
* **Provide specific examples to demonstrate the enhancement**
* **Describe the current behavior and explain the expected behavior**
* **Explain why this enhancement would be useful**

### Pull Requests

1. Fork the repo and create your branch from `main`
2. If you've added code that should be tested, add tests
3. If you've changed APIs, update the documentation
4. Ensure the test suite passes
5. Make sure your code follows the style guidelines
6. Issue that pull request!

## Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/learning-agent.git
   cd learning-agent
   ```

2. **Install uv package manager**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Install dependencies**
   ```bash
   uv sync --all-extras
   ```

4. **Set up pre-commit hooks**
   ```bash
   make pre-commit-install
   ```

5. **Create a branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Workflow

### Before Committing

1. **Format your code**
   ```bash
   make format
   ```

2. **Run linting**
   ```bash
   make lint
   ```

3. **Run type checking**
   ```bash
   make typecheck
   ```

4. **Run tests**
   ```bash
   make test
   ```

5. **Check for security issues**
   ```bash
   make security
   ```

Or run all checks at once:
```bash
make check
```

### Testing

We use a hybrid testing approach:

#### Traditional Tests
```bash
make test-unit        # Unit tests
make test-integration # Integration tests
make test-cov        # Tests with coverage
```

#### LangSmith Probabilistic Tests
```bash
make langsmith-test  # Run probabilistic tests
```

See [tests/README.md](tests/README.md) for detailed testing guidelines.

### Code Style

* We use [Ruff](https://github.com/astral-sh/ruff) for linting and formatting
* We use [mypy](http://mypy-lang.org/) for type checking
* Follow PEP 8 with a line length of 100 characters
* Use type hints for all function signatures
* Write docstrings for all public functions and classes

### Documentation

* Update the README.md if you change functionality
* Add docstrings to new functions and classes
* Update type hints if you change function signatures
* Add examples for new features

### Commit Messages

* Use the present tense ("Add feature" not "Added feature")
* Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
* Limit the first line to 72 characters or less
* Reference issues and pull requests liberally after the first line

Example:
```
Add parallel execution for independent todos

- Implement Send API for LangGraph orchestration
- Add dependency resolution for todo items
- Update tests for parallel execution

Fixes #123
```

## Project Structure

```
learning-agent/
├── src/learning_agent/     # Main package
│   ├── supervisor/         # Main orchestrator
│   ├── learning/          # Learning and memory systems
│   ├── orchestration/     # Task orchestration
│   ├── agents/           # Sub-agent implementations
│   ├── tools/            # Tool implementations
│   └── providers/        # LLM and embedding providers
├── tests/                # Test suite
│   ├── test_unit.py     # Unit tests
│   ├── test_integration.py # Integration tests
│   └── langsmith_eval.py # Probabilistic tests
├── docs/                # Documentation
└── .github/            # GitHub specific files
```

## Key Areas for Contribution

### High Priority
- [ ] Implement long-term memory consolidation
- [ ] Add support for more LLM providers
- [ ] Improve pattern recognition algorithms
- [ ] Add more comprehensive tests

### Good First Issues
- [ ] Improve documentation
- [ ] Add more examples
- [ ] Fix typos and small bugs
- [ ] Add input validation

### Advanced Features
- [ ] Implement collaborative multi-agent learning
- [ ] Add web UI for monitoring
- [ ] Implement custom tool creation API
- [ ] Add support for multimodal inputs

## Questions?

Feel free to open an issue with the label "question" or reach out on our discussions page.

## Recognition

Contributors will be recognized in our README and release notes. Thank you for your contributions!
