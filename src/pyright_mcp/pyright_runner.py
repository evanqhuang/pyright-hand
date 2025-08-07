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
    print(f"DEBUG: execute_pyright called with project_path={project_path}, severity={severity}, pyright_path={pyright_path}")
    # Find pyright executable
    command: list[str]
    if pyright_path:
        command = [pyright_path]
    else:
        pyright_cmd = shutil.which("pyright")
        if pyright_cmd:
            # Use node directly to run pyright script to avoid env issues
            node_cmd = shutil.which("node")
            if node_cmd:
                command = [node_cmd, pyright_cmd]
            else:
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
        # Run Pyright with explicit PATH environment
        import os
        env = os.environ.copy()
        # Ensure /usr/bin is in PATH for env to find node
        if '/usr/bin' not in env.get('PATH', ''):
            env['PATH'] = f"/usr/bin:{env.get('PATH', '')}"
        
        # Debug: print the command being executed
        print(f"DEBUG: Executing command: {command}")
        print(f"DEBUG: Working directory: {project_path}")
        print(f"DEBUG: PATH: {env.get('PATH')}")
            
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=project_path,
            timeout=300,  # 5 minute timeout
            env=env,
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