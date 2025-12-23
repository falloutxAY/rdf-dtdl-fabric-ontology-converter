# Contributing to RDF to Fabric Ontology Converter

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Maintain professional communication

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/yourusername/repo/issues)
2. If not, create a new issue with:
   - Clear descriptive title
   - Steps to reproduce
   - Expected vs actual behavior
   - Python version and OS
   - Error messages/logs
   - Sample files (if applicable)

### Suggesting Features

1. Open an issue with the `enhancement` label
2. Describe the feature and its use case
3. Explain why it would be valuable
4. Consider implementation approach

### Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Write/update tests
5. Update documentation
6. Run tests: `python run_tests.py all`
7. Commit: `git commit -m 'Add amazing feature'`
8. Push: `git push origin feature/amazing-feature`
9. Open a Pull Request

## Development Setup

### Prerequisites
- Python 3.9+
- Git
- Virtual environment tool

### Setup Steps

```bash
# 1. Fork and clone
git clone https://github.com/yourusername/rdf-fabric-ontology-converter.git
cd rdf-fabric-ontology-converter

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # If available

# 4. Install pre-commit hooks (optional)
pip install pre-commit
pre-commit install

# 5. Run tests
python run_tests.py all
```

## Coding Standards

### Python Style

- Follow [PEP 8](https://pep8.org/)
- Use type hints where appropriate
- Maximum line length: 100 characters
- Use descriptive variable names

### Code Structure

```python
"""Module docstring describing purpose."""

import standard_library
import third_party
import local_modules


class MyClass:
    """Class docstring."""
    
    def __init__(self, param: str):
        """Initialize with parameter."""
        self.param = param
    
    def my_method(self) -> str:
        """Method docstring describing behavior."""
        return self.param


def my_function(arg: str) -> bool:
    """
    Function docstring with detailed description.
    
    Args:
        arg: Description of argument
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When arg is invalid
    """
    if not arg:
        raise ValueError("arg cannot be empty")
    return True
```

### Documentation

- Add docstrings to all public functions/classes
- Use Google-style or NumPy-style docstrings
- Update README.md for user-facing changes
- Add examples for new features
- Update API_REFERENCE.md for new functions

### Testing

- Write tests for new features
- Maintain test coverage above 80%
- Test edge cases and error conditions
- Use descriptive test names

```python
def test_feature_description(self):
    """Test that feature behaves correctly under condition."""
    # Arrange
    input_data = "test"
    
    # Act
    result = my_function(input_data)
    
    # Assert
    assert result == expected_output
```

### Commit Messages

Use clear, descriptive commit messages:

```
feat: Add support for OWL unionOf constructs

- Parse unionOf statements in TTL
- Convert to Fabric entity types
- Add tests for union classes
- Update documentation

Fixes #123
```

Prefix types:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Test additions/changes
- `refactor:` - Code refactoring
- `style:` - Code style changes
- `chore:` - Build/tooling changes

## Project Structure

### Source Code (`src/`)
- `main.py` - CLI entry point
- `rdf_converter.py` - Core conversion logic
- `fabric_client.py` - API client

### Tests (`tests/`)
- `test_converter.py` - Unit tests
- `test_integration.py` - Integration tests
- `run_tests.py` - Test runner

### Documentation (`docs/`)
- User guides and references
- Should be updated with code changes

### Samples (`samples/`)
- Example ontology files
- Used in tests

## Testing Guidelines

### Running Tests

```bash
# All tests
python run_tests.py all

# Specific category
python run_tests.py core
python run_tests.py samples

# With coverage
python -m pytest --cov=src --cov-report=html

# Specific test
python -m pytest tests/test_converter.py::test_name -v
```

### Writing Tests

1. Add tests in `tests/` directory
2. Follow existing test structure
3. Use fixtures for common setup
4. Test both success and failure cases
5. Include docstrings

### Test Coverage

- Aim for >80% code coverage
- All new features must have tests
- Bug fixes should include regression tests

## Pull Request Process

1. **Before submitting:**
   - Run all tests: `python run_tests.py all`
   - Update documentation
   - Add changelog entry (if applicable)
   - Ensure code follows style guidelines

2. **PR Description should include:**
   - What changed and why
   - Related issue numbers
   - Testing performed
   - Screenshots (if UI changes)
   - Breaking changes (if any)

3. **Review process:**
   - Maintainers will review within 1-2 weeks
   - Address review feedback
   - Keep PR focused and small
   - Rebase if needed

4. **After merge:**
   - Delete your feature branch
   - Update your fork's main branch

## Release Process

Maintainers will:
1. Update version number
2. Update CHANGELOG.md
3. Create GitHub release
4. Tag release: `git tag v1.2.3`

## Getting Help

- Ask questions in [Discussions](https://github.com/yourusername/repo/discussions)
- Chat on [Discord/Slack] (if available)
- Email maintainers (see README)

## Recognition

Contributors will be:
- Listed in README.md
- Mentioned in release notes
- Credited in commit history

## License

By contributing, you agree that your contributions will be licensed under the same MIT License that covers the project.

---

Thank you for contributing! 🎉
