"""Tests for MCP server functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pyright_mcp.models import PyrightResult
from pyright_mcp.server import check_python_types, list_python_files, paginate_diagnostics, transform_pyright_output


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
                ctx=ctx,
                severity_level="warning"
            )
        
            assert isinstance(result, PyrightResult)
            assert result.summary.filesAnalyzed == 2
            
            # Check context calls
            ctx.info.assert_called()
            ctx.report_progress.assert_called()
    
    @patch("pyright_mcp.server.find_python_files")
    @patch("pyright_mcp.server.execute_pyright")
    async def test_check_python_types_single_file(self, mock_execute, mock_find_files):
        """Test checking a single Python file."""
        mock_find_files.return_value = ["/app/code/app.py"]
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
            mock_file.__str__ = MagicMock(return_value="/app/code")
            mock_path.return_value = mock_file
            
            result = await check_python_types(
                ctx=ctx
            )
            
            assert isinstance(result, PyrightResult)
            mock_execute.assert_called_once_with("/app/code", "warning")
    
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
            mock_dir.__str__ = MagicMock(return_value="/app/code")  # Make sure this returns the expected path
            mock_path.return_value = mock_dir
            
            files = await list_python_files(
                ctx=ctx
            )
            
            assert len(files) == 2
            assert "/test/file1.py" in files
            mock_find_files.assert_called_once_with("/app/code", None)
    


class TestServerPagination:
    """Test pagination functionality."""

    def test_paginate_diagnostics_basic(self):
        """Test basic pagination of diagnostics."""
        from pyright_mcp.models import Diagnostic, DiagnosticRange
        
        # Create sample diagnostics
        diagnostics = []
        for i in range(25):
            diagnostic = Diagnostic(
                file=f"/test/file{i}.py",
                severity="error",
                message=f"Error {i}",
                rule="testRule",
                range=DiagnosticRange(
                    start={"line": i, "character": 0},
                    end={"line": i, "character": 10}
                )
            )
            diagnostics.append(diagnostic)
        
        # Test first page
        paginated, pagination = paginate_diagnostics(diagnostics, page=1, page_size=10)
        
        assert len(paginated) == 10
        assert pagination.current_page == 1
        assert pagination.total_pages == 3
        assert pagination.page_size == 10
        assert pagination.total_diagnostics == 25
        assert pagination.has_next_page is True
        assert pagination.has_previous_page is False
        assert paginated[0].file == "/test/file0.py"
        assert paginated[9].file == "/test/file9.py"

    def test_paginate_diagnostics_middle_page(self):
        """Test middle page pagination."""
        from pyright_mcp.models import Diagnostic, DiagnosticRange
        
        diagnostics = []
        for i in range(25):
            diagnostic = Diagnostic(
                file=f"/test/file{i}.py",
                severity="error", 
                message=f"Error {i}",
                rule="testRule",
                range=DiagnosticRange(
                    start={"line": i, "character": 0},
                    end={"line": i, "character": 10}
                )
            )
            diagnostics.append(diagnostic)
        
        # Test middle page
        paginated, pagination = paginate_diagnostics(diagnostics, page=2, page_size=10)
        
        assert len(paginated) == 10
        assert pagination.current_page == 2
        assert pagination.total_pages == 3
        assert pagination.has_next_page is True
        assert pagination.has_previous_page is True
        assert paginated[0].file == "/test/file10.py"
        assert paginated[9].file == "/test/file19.py"

    def test_paginate_diagnostics_last_page(self):
        """Test last page with partial results."""
        from pyright_mcp.models import Diagnostic, DiagnosticRange
        
        diagnostics = []
        for i in range(25):
            diagnostic = Diagnostic(
                file=f"/test/file{i}.py",
                severity="error",
                message=f"Error {i}",
                rule="testRule",
                range=DiagnosticRange(
                    start={"line": i, "character": 0},
                    end={"line": i, "character": 10}
                )
            )
            diagnostics.append(diagnostic)
        
        # Test last page
        paginated, pagination = paginate_diagnostics(diagnostics, page=3, page_size=10)
        
        assert len(paginated) == 5  # Only 5 items on last page
        assert pagination.current_page == 3
        assert pagination.total_pages == 3
        assert pagination.has_next_page is False
        assert pagination.has_previous_page is True
        assert paginated[0].file == "/test/file20.py"
        assert paginated[4].file == "/test/file24.py"

    def test_paginate_diagnostics_empty(self):
        """Test pagination with empty diagnostics list."""
        diagnostics = []
        
        paginated, pagination = paginate_diagnostics(diagnostics, page=1, page_size=10)
        
        assert len(paginated) == 0
        assert pagination.current_page == 1
        assert pagination.total_pages == 1
        assert pagination.total_diagnostics == 0
        assert pagination.has_next_page is False
        assert pagination.has_previous_page is False

    def test_transform_pyright_output_with_pagination(self):
        """Test transform function with pagination."""
        raw_output = {
            "version": "1.1.300",
            "generalDiagnostics": [
                {
                    "file": "/test/file1.py",
                    "severity": "error",
                    "message": "Error 1",
                    "rule": "rule1",
                    "range": {
                        "start": {"line": 1, "character": 0},
                        "end": {"line": 1, "character": 10}
                    }
                },
                {
                    "file": "/test/file2.py", 
                    "severity": "warning",
                    "message": "Warning 1",
                    "rule": "rule2",
                    "range": {
                        "start": {"line": 2, "character": 0},
                        "end": {"line": 2, "character": 10}
                    }
                },
                {
                    "file": "/test/file3.py",
                    "severity": "error", 
                    "message": "Error 2",
                    "rule": "rule3",
                    "range": {
                        "start": {"line": 3, "character": 0},
                        "end": {"line": 3, "character": 10}
                    }
                }
            ],
            "summary": {
                "filesAnalyzed": 3,
                "errorCount": 2,
                "warningCount": 1,
                "informationCount": 0,
                "timeInSec": 1.0
            }
        }
        
        result = transform_pyright_output(raw_output, page=1, page_size=2)
        
        assert len(result.diagnostics) == 2  # Page size limit
        assert result.pagination is not None
        assert result.pagination.current_page == 1
        assert result.pagination.total_pages == 2
        assert result.pagination.total_diagnostics == 3
        assert result.pagination.has_next_page is True
        assert result.pagination.has_previous_page is False