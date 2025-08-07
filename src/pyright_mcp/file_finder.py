"""File discovery utilities for Python files."""

import os
from pathlib import Path
from typing import Optional

from pathspec import PathSpec
from pathspec.patterns.gitwildmatch import GitWildMatchPattern


def find_python_files(
    root_dir: str,
    custom_ignore_patterns: Optional[list[str]] = None,
) -> list[str]:
    """
    Find all Python files in a directory tree.
    
    Args:
        root_dir: Root directory to search
        custom_ignore_patterns: Additional patterns to ignore
        
    Returns:
        List of absolute paths to Python files
    """
    root_path = Path(root_dir).resolve()
    
    if not root_path.exists():
        raise FileNotFoundError(f"Directory not found: {root_dir}")
    
    ignore_patterns = [
        "__pycache__",
        "*.pyc",
        ".git",
        ".venv",
        "venv",
        "env",
        ".env",
        "node_modules",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "dist",
        "build",
        "*.egg-info",
    ]
    
    if custom_ignore_patterns:
        ignore_patterns.extend(custom_ignore_patterns)
    
    # Check for .gitignore
    gitignore_path = root_path / ".gitignore"
    if gitignore_path.exists():
        with open(gitignore_path, "r", encoding="utf-8") as f:
            gitignore_lines = [
                line.strip()
                for line in f
                if line.strip() and not line.startswith("#")
            ]
            ignore_patterns.extend(gitignore_lines)
    
    spec = PathSpec.from_lines(GitWildMatchPattern, ignore_patterns)
    
    python_files = []
    
    for dirpath, dirnames, filenames in os.walk(root_path):
        # Filter directories to skip
        dirnames[:] = [
            d for d in dirnames
            if not spec.match_file(os.path.join(dirpath, d))
        ]
        
        for filename in filenames:
            if filename.endswith((".py", ".pyi")):
                full_path = os.path.join(dirpath, filename)
                relative_path = os.path.relpath(full_path, root_path)
                
                if not spec.match_file(relative_path):
                    python_files.append(full_path)
    
    return sorted(python_files)