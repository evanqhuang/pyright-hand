"""Pyright execution and output parsing."""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Optional


def execute_pyright(
    project_path: str,
    severity: str = "warning",
    pyright_path: Optional[str] = None,
) -> dict[str, Any]:
    """
    Execute Pyright on a project and return JSON output.
    
    Args:
        project_path: Path to the project to analyze
        severity: Minimum severity level (error, warning, information)
        pyright_path: Optional custom path to pyright executable
        
    Returns:
        Parsed JSON output from Pyright
        
    Raises:
        RuntimeError: If Pyright is not found or execution fails
    """
    # Find pyright executable
    command: list[str]
    if pyright_path:
        command = [pyright_path]
    else:
        pyright_cmd = shutil.which("pyright")
        if pyright_cmd:
            command = [pyright_cmd]
        else:
            # Try npx as fallback
            npx_cmd = shutil.which("npx")
            if npx_cmd:
                command = [npx_cmd, "pyright"]
            else:
                raise RuntimeError(
                    "Pyright not found. Please install it via 'npm install -g pyright' "
                    "or 'pip install pyright'"
                )
    
    command.extend([
        project_path,
        "--outputjson",
        f"--level={severity}",
    ])
    
    # Check for pyrightconfig.json in project
    config_path = Path(project_path) / "pyrightconfig.json"
    if config_path.exists():
        command.extend(["--project", str(config_path)])
    
    try:
        # Run Pyright
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=project_path,
            timeout=300,  # 5 minute timeout
        )
        
        # Pyright returns non-zero on errors/warnings, but still produces JSON
        if result.stdout:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError as e:
                # If JSON parsing fails, provide helpful error
                raise RuntimeError(
                    f"Failed to parse Pyright output: {e}\n"
                    f"Output: {result.stdout[:500]}"
                )
        
        # No output usually means no Python files or fatal error
        if result.stderr:
            raise RuntimeError(f"Pyright error: {result.stderr}")
            
        # Empty project
        return {
            "version": "unknown",
            "time": "0",
            "generalDiagnostics": [],
            "summary": {
                "filesAnalyzed": 0,
                "errorCount": 0,
                "warningCount": 0,
                "informationCount": 0,
                "timeInSec": 0,
            }
        }
        
    except subprocess.TimeoutExpired:
        raise RuntimeError("Pyright execution timed out after 5 minutes")
    except FileNotFoundError:
        raise RuntimeError(f"Command not found: {command[0]}")