# Pyright Hand MCP Server

A Model Context Protocol (MCP) server that provides Python type checking capabilities for the entire codebase using Pyright. A problem I frequently run into when using agentic AI is that it constantly spits out code with numerous type safety errors, and no amount of prompting or guiding will make it continually verify the file. This MCP will expose a tool to the agent that will provide Pyright analysis of all files so it can continously check the entire project for type errors. 

## Features

- **Type Checking**: Run Pyright analysis on Python projects
- **File Discovery**: Automatically find Python files while respecting .gitignore
- **Structured Output**: Return detailed diagnostic information in a structured format
- **Multiple Transports**: Support for stdio, SSE, and HTTP transports
- **Progress Reporting**: Real-time progress updates during analysis
- **Configurable Severity**: Filter results by error, warning, or information level


## Prerequisites

Pyright must be installed and available in your PATH:

```bash
# Via npm (recommended)
npm install -g pyright

# Or via pip
pip install pyright
```

## Docker Usage

This server is designed to run in a Docker container, analyzing a Python codebase mounted as a volume.

### Example MCP Configuration for Claude

Here is an example of how to configure this tool for use with an AI assistant:

```json
{
    "mcpServers": {
        "pyright-hand-mcp": {
            "command": "docker",
            "args": [
                "run",
                "-i",
                "-v",
                "/Users/username/your/project:/app/code",
                "--rm",
                "evanhuang117/pyright-hand-mcp-server"
            ]
        }
    }
}
```

Replace `/path/to/your/python/project` with the actual path to the code you want to analyze.

## Tools Available

#### `check_python_types`

Analyzes Python files in the `/app/code` directory for type errors.

**Parameters:**
- `severity_level` (string, optional): Minimum severity level ("error", "warning", "information"). Default: "warning"
- `ignore_patterns` (list[string], optional): Additional glob patterns to ignore

**Returns:**
- Structured results with summary statistics and detailed diagnostics

#### `list_python_files`

Lists all Python files in the `/app/code` directory that would be analyzed.

**Parameters:**
- `ignore_patterns` (list[string], optional): Additional glob patterns to ignore

**Returns:**
- List of Python file paths

## Example Usage

```python
# Example of calling the tool via MCP
result = await session.call_tool("check_python_types", {
    "severity_level": "warning",
    "ignore_patterns": ["tests/*.py"]
})

print(f"Found {result.summary.errorCount} errors")
for diagnostic in result.diagnostics:
    print(f"{diagnostic.file}:{diagnostic.range.start['line']} - {diagnostic.message}")
```

## Configuration

The server respects:
- `.gitignore` files for automatic file exclusion
- `pyrightconfig.json` for Pyright-specific configuration
- Standard ignore patterns (\_\_pycache\_\_, .venv, etc.)

## Development

```bash
pip install -e ".[dev]"
```

Run tests:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=pyright_mcp
```

Format code:

```bash
black src/ tests/
ruff check src/ tests/
```

## License

MIT License - see LICENSE file for details.
