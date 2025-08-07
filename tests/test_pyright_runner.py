"""Tests for Pyright runner functionality."""

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from pyright_mcp.pyright_runner import execute_pyright


class TestPyrightRunner:
    """Test Pyright execution functionality."""
    
    @patch("pyright_mcp.pyright_runner.subprocess.run")
    @patch("pyright_mcp.pyright_runner.shutil.which")
    def test_execute_pyright_success(self, mock_which, mock_run):
        """Test successful Pyright execution."""
        mock_which.return_value = "/usr/bin/pyright"
        
        expected_output = {
            "version": "1.1.300",
            "time": "1.5",
            "generalDiagnostics": [
                {
                    "file": "test.py",
                    "severity": "error",
                    "message": "Type error",
                    "rule": "reportGeneralTypeIssues",
                    "range": {
                        "start": {"line": 10, "character": 5},
                        "end": {"line": 10, "character": 15}
                    }
                }
            ],
            "summary": {
                "filesAnalyzed": 1,
                "errorCount": 1,
                "warningCount": 0,
                "informationCount": 0,
                "timeInSec": 1.5
            }
        }
        
        mock_result = MagicMock()
        mock_result.stdout = json.dumps(expected_output)
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        result = execute_pyright("/path/to/project")
        
        assert result == expected_output
        mock_run.assert_called_once()
        
        # Check command
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "/usr/bin/pyright"
        assert "/path/to/project" in call_args
        assert "--outputjson" in call_args
        assert "--level=warning" in call_args
    
    @patch("pyright_mcp.pyright_runner.subprocess.run")
    @patch("pyright_mcp.pyright_runner.shutil.which")
    def test_execute_pyright_custom_severity(self, mock_which, mock_run):
        """Test Pyright with custom severity level."""
        mock_which.return_value = "/usr/bin/pyright"
        
        mock_result = MagicMock()
        mock_result.stdout = json.dumps({"summary": {}})
        mock_run.return_value = mock_result
        
        execute_pyright("/path", severity="error")
        
        call_args = mock_run.call_args[0][0]
        assert "--level=error" in call_args
    
    @patch("pyright_mcp.pyright_runner.subprocess.run")
    @patch("pyright_mcp.pyright_runner.shutil.which")
    def test_execute_pyright_npx_fallback(self, mock_which, mock_run):
        """Test falling back to npx when pyright not found."""
        def which_side_effect(cmd):
            if cmd == "pyright":
                return None
            if cmd == "npx":
                return "/usr/bin/npx"
            return None
        
        mock_which.side_effect = which_side_effect
        
        mock_result = MagicMock()
        mock_result.stdout = json.dumps({"summary": {}})
        mock_run.return_value = mock_result
        
        execute_pyright("/path")
        
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "/usr/bin/npx"
        assert call_args[1] == "pyright"
    
    @patch("pyright_mcp.pyright_runner.shutil.which")
    def test_execute_pyright_not_found(self, mock_which):
        """Test error when Pyright is not found."""
        mock_which.return_value = None
        
        with pytest.raises(RuntimeError, match="Pyright not found"):
            execute_pyright("/path")
    
    @patch("pyright_mcp.pyright_runner.subprocess.run")
    @patch("pyright_mcp.pyright_runner.shutil.which")
    def test_execute_pyright_invalid_json(self, mock_which, mock_run):
        """Test handling of invalid JSON output."""
        mock_which.return_value = "/usr/bin/pyright"
        
        mock_result = MagicMock()
        mock_result.stdout = "Invalid JSON {{"
        mock_run.return_value = mock_result
        
        with pytest.raises(RuntimeError, match="Failed to parse Pyright output"):
            execute_pyright("/path")
    
    @patch("pyright_mcp.pyright_runner.subprocess.run")
    @patch("pyright_mcp.pyright_runner.shutil.which")
    def test_execute_pyright_timeout(self, mock_which, mock_run):
        """Test timeout handling."""
        mock_which.return_value = "/usr/bin/pyright"
        mock_run.side_effect = subprocess.TimeoutExpired(["pyright"], 300)
        
        with pytest.raises(RuntimeError, match="timed out"):
            execute_pyright("/path")
    
    @patch("pyright_mcp.pyright_runner.subprocess.run")
    @patch("pyright_mcp.pyright_runner.shutil.which")
    def test_execute_pyright_empty_project(self, mock_which, mock_run):
        """Test handling of empty project."""
        mock_which.return_value = "/usr/bin/pyright"
        
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        result = execute_pyright("/path")
        
        assert result["generalDiagnostics"] == []
        assert result["summary"]["filesAnalyzed"] == 0