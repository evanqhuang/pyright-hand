# Contributing to Pyright MCP Server

## Development Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd pyright-mcp
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install in development mode:
```bash
pip install -e ".[dev]"
```

## Prerequisites

Make sure you have Pyright installed:
```bash
# Via npm (recommended)
npm install -g pyright

# Or via pip
pip install pyright
```

## Running Tests

Run the full test suite:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=pyright_mcp --cov-report=html
```

Run type checking:
```bash
mypy src/
```

## Code Quality

Format code:
```bash
black src/ tests/
```

Lint code:
```bash
ruff check src/ tests/
```

## Testing the Server

You can test the server manually with:
```bash
python test_server.py
```

Or run it as an MCP server:
```bash
python -m pyright_mcp.main
```

## Project Structure

```
src/pyright_mcp/
├── __init__.py          # Package init
├── main.py              # CLI entry point
├── server.py            # MCP server with tools
├── models.py            # Data models
├── file_finder.py       # Python file discovery
└── pyright_runner.py    # Pyright execution
```

## Adding New Features

1. Update relevant models in `models.py` if needed
2. Implement functionality in appropriate modules
3. Add comprehensive tests
4. Update documentation

## Pull Request Guidelines

1. Ensure all tests pass
2. Add tests for new functionality
3. Update documentation
4. Follow existing code style
5. Keep commits atomic and well-described