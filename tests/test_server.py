"""Tests for MCP server functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pyright_mcp.models import PyrightResult
from pyright_mcp.server import check_python_types, list_python_files, transform_pyright_output


class TestServerTransform:
    """Test output transformation."""
    
    def test_transform_pyright_output_complete(self):
        """Test transformation of complete Pyright output."""
        raw_output = {
            "version": "1.1.300",
            "time": "2.5",
            "generalDiagnostics": [
                {
                    "file": "/path/to/file.py",
                    "severity": "error",
                    "message": "Type mismatch",
                    "rule": "reportGeneralTypeIssues",
                    "range": {
                        "start": {"line": 10, "character": 5},
                        "end": {"line": 10, "character": 15}
                    }
                },
                {
                    "file": "/path/to/other.py",
                    "severity": "warning",
                    "message": "Variable unused",
                    "rule": "reportUnusedVariable",
                    "range": {
                        "start": {"line": 20, "character": 0},
                        "end": {"line": 20, "character": 10}
                    }
                }
            ],
            "summary": {
                "filesAnalyzed": 5,
                "errorCount": 1,
                "warningCount": 1,
                "informationCount": 0,
                "timeInSec": 2.5
            }
        }
        
        result = transform_pyright_output(raw_output)
        
        assert isinstance(result, PyrightResult)
        assert result.version == "1.1.300"
        assert result.summary.filesAnalyzed == 5
        assert result.summary.errorCount == 1
        assert result.summary.warningCount == 1
        assert len(result.diagnostics) == 2
        
        # Check first diagnostic
        diag = result.diagnostics[0]
        assert diag.file == "/path/to/file.py"
        assert diag.severity == "error"
        assert diag.message == "Type mismatch"
        assert diag.rule == "reportGeneralTypeIssues"
        assert diag.range.start["line"] == 10
    
    def test_transform_pyright_output_minimal(self):
        """Test transformation with minimal output."""
        raw_output = {
            "generalDiagnostics": [],
            "summary": {}
        }
        
        result = transform_pyright_output(raw_output)
        
        assert result.summary.filesAnalyzed == 0
        assert result.summary.errorCount == 0
        assert len(result.diagnostics) == 0
        assert result.version is None
    
    def test_transform_pyright_output_skip_no_file(self):
        """Test skipping diagnostics without file."""
        raw_output = {
            "generalDiagnostics": [
                {
                    "severity": "error",
                    "message": "General error"
                },
                {
                    "file": "/path/to/file.py",
                    "severity": "warning",
                    "message": "Valid diagnostic"
                }
            ],
            "summary": {}
        }
        
        result = transform_pyright_output(raw_output)
        
        # Should only include diagnostic with file
        assert len(result.diagnostics) == 1
        assert result.diagnostics[0].file == "/path/to/file.py"


@pytest.mark.asyncio
class TestServerTools:
    """Test MCP tool implementations."""
    
    @patch("pyright_mcp.server.execute_pyright")
    @patch("pyright_mcp.server.find_python_files")
    async def test_check_python_types_success(self, mock_find_files, mock_execute):
        """Test successful type checking."""
        mock_find_files.return_value = ["file1.py", "file2.py"]
        mock_execute.return_value = {
            "generalDiagnostics": [],
            "summary": {
                "filesAnalyzed": 2,
                "errorCount": 0,
                "warningCount": 0,
                "informationCount": 0,
                "timeInSec": 1.0
            }
        }
        
        ctx = AsyncMock()
        
        with patch("pyright_mcp.server.Path") as mock_path:
            mock_dir = MagicMock()
            mock_dir.resolve.return_value = mock_dir
            mock_dir.exists.return_value = True
            mock_dir.is_file.return_value = False
            mock_path.return_value = mock_dir
            
            result = await check_python_types(
                path="/test/path",
                ctx=ctx,
                severity_level="warning"
            )
        
            assert isinstance(result, PyrightResult)
            assert result.summary.filesAnalyzed == 2
            
            # Check context calls
            ctx.info.assert_called()
            ctx.report_progress.assert_called()
    
    @patch("pyright_mcp.server.execute_pyright")
    async def test_check_python_types_single_file(self, mock_execute):
        """Test checking a single Python file."""
        mock_execute.return_value = {
            "generalDiagnostics": [],
            "summary": {"filesAnalyzed": 1}
        }
        
        ctx = AsyncMock()
        
        with patch("pyright_mcp.server.Path") as mock_path:
            mock_file = MagicMock()
            mock_file.resolve.return_value = mock_file
            mock_file.exists.return_value = True
            mock_file.is_file.return_value = True
            mock_file.suffix = ".py"
            mock_file.parent = "/test"
            mock_path.return_value = mock_file
            
            result = await check_python_types(
                path="/test/file.py",
                ctx=ctx
            )
            
            assert isinstance(result, PyrightResult)
            mock_execute.assert_called_once_with("/test", "warning")
    
    async def test_check_python_types_not_found(self):
        """Test error when path doesn't exist."""
        ctx = AsyncMock()
        
        with patch("pyright_mcp.server.Path") as mock_path:
            mock_file = MagicMock()
            mock_file.resolve.return_value = mock_file
            mock_file.exists.return_value = False
            mock_path.return_value = mock_file
            
            with pytest.raises(FileNotFoundError):
                await check_python_types(
                    path="/nonexistent",
                    ctx=ctx
                )
    
    async def test_check_python_types_not_python_file(self):
        """Test error for non-Python file."""
        ctx = AsyncMock()
        
        with patch("pyright_mcp.server.Path") as mock_path:
            mock_file = MagicMock()
            mock_file.resolve.return_value = mock_file
            mock_file.exists.return_value = True
            mock_file.is_file.return_value = True
            mock_file.suffix = ".txt"
            mock_path.return_value = mock_file
            
            with pytest.raises(ValueError, match="Not a Python file"):
                await check_python_types(
                    path="/test/file.txt",
                    ctx=ctx
                )
    
    @patch("pyright_mcp.server.find_python_files")
    async def test_list_python_files_directory(self, mock_find_files):
        """Test listing Python files in directory."""
        mock_find_files.return_value = [
            "/test/file1.py",
            "/test/file2.py"
        ]
        
        ctx = AsyncMock()
        
        with patch("pyright_mcp.server.Path") as mock_path:
            mock_dir = MagicMock()
            mock_dir.resolve.return_value = mock_dir
            mock_dir.exists.return_value = True
            mock_dir.is_file.return_value = False
            mock_dir.__str__.return_value = "/test/path"  # Add string representation
            mock_path.return_value = mock_dir
            
            files = await list_python_files(
                path="/test",
                ctx=ctx
            )
            
            assert len(files) == 2
            assert "/test/file1.py" in files
            mock_find_files.assert_called_once_with(str(mock_dir), None)
    
    async def test_list_python_files_single_file(self):
        """Test listing single Python file."""
        ctx = AsyncMock()
        
        with patch("pyright_mcp.server.Path") as mock_path:
            mock_file = MagicMock()
            mock_file.resolve.return_value = mock_file
            mock_file.exists.return_value = True
            mock_file.is_file.return_value = True
            mock_file.suffix = ".py"
            mock_file.__str__.return_value = "/test/file.py"
            mock_path.return_value = mock_file
            
            files = await list_python_files(
                path="/test/file.py",
                ctx=ctx
            )
            
            assert files == ["/test/file.py"]