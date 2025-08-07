"""Tests for file finding functionality."""

import os
import tempfile
from pathlib import Path

import pytest

from pyright_mcp.file_finder import find_python_files


class TestFileFinder:
    """Test file discovery functionality."""
    
    @pytest.fixture
    def temp_project(self):
        """Create a temporary project structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            
            # Create Python files
            (root / "main.py").write_text("print('main')")
            (root / "utils.py").write_text("def helper(): pass")
            
            # Create subdirectory with files
            subdir = root / "src"
            subdir.mkdir()
            (subdir / "module.py").write_text("class MyClass: pass")
            (subdir / "types.pyi").write_text("from typing import Any")
            
            # Create ignored directories
            venv = root / "venv"
            venv.mkdir()
            (venv / "lib.py").write_text("# Should be ignored")
            
            cache = root / "__pycache__"
            cache.mkdir()
            (cache / "cached.py").write_text("# Should be ignored")
            
            # Create .gitignore
            (root / ".gitignore").write_text("*.log\ntemp/\n")
            
            # Create temp directory (should be ignored by gitignore)
            temp = root / "temp"
            temp.mkdir()
            (temp / "temp.py").write_text("# Should be ignored")
            
            yield root
    
    def test_find_python_files_basic(self, temp_project):
        """Test finding Python files in a basic project."""
        files = find_python_files(str(temp_project))
        
        # Convert to relative paths for easier testing
        relative_files = [
            Path(f).relative_to(Path(temp_project).resolve()).as_posix()
            for f in files
        ]
        
        expected = ["main.py", "src/module.py", "src/types.pyi", "utils.py"]
        assert sorted(relative_files) == sorted(expected)
    
    def test_find_python_files_with_custom_ignore(self, temp_project):
        """Test custom ignore patterns."""
        files = find_python_files(
            str(temp_project),
            custom_ignore_patterns=["utils.py", "src/*.pyi"]
        )
        
        relative_files = [
            Path(f).relative_to(Path(temp_project).resolve()).as_posix()
            for f in files
        ]
        
        expected = ["main.py", "src/module.py"]
        assert sorted(relative_files) == sorted(expected)
    
    def test_find_python_files_nonexistent_dir(self):
        """Test handling of non-existent directory."""
        with pytest.raises(FileNotFoundError):
            find_python_files("/nonexistent/path")
    
    def test_find_python_files_empty_dir(self):
        """Test empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            files = find_python_files(tmpdir)
            assert files == []
    
    def test_find_python_files_single_file(self):
        """Test directory with single Python file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "single.py").write_text("x = 1")
            
            files = find_python_files(tmpdir)
            assert len(files) == 1
            assert files[0].endswith("single.py")