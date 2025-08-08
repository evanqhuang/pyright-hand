"""MCP server implementation for Pyright."""

import logging
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import Context, FastMCP

from .file_finder import find_python_files
from .models import Diagnostic, DiagnosticRange, PaginationInfo, PyrightResult, PyrightSummary
from .pyright_runner import execute_pyright

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the MCP server
mcp = FastMCP("Pyright-hand Python Checker")


def paginate_diagnostics(
    diagnostics: list[Diagnostic], 
    page: int, 
    page_size: int
) -> tuple[list[Diagnostic], PaginationInfo]:
    """
    Paginate diagnostics and return page info.
    
    Args:
        diagnostics: Full list of diagnostics
        page: Page number (1-based)
        page_size: Number of items per page
        
    Returns:
        Tuple of (paginated_diagnostics, pagination_info)
    """
    total_diagnostics = len(diagnostics)
    total_pages = max(1, (total_diagnostics + page_size - 1) // page_size)
    
    # Validate page number
    page = max(1, min(page, total_pages))
    
    # Calculate pagination
    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, total_diagnostics)
    
    paginated_diagnostics = diagnostics[start_idx:end_idx]
    
    pagination_info = PaginationInfo(
        current_page=page,
        total_pages=total_pages,
        page_size=page_size,
        total_diagnostics=total_diagnostics,
        has_next_page=page < total_pages,
        has_previous_page=page > 1
    )
    
    return paginated_diagnostics, pagination_info


def transform_pyright_output(raw_output: dict, page: int = 1, page_size: int = 50) -> PyrightResult:
    """
    Transform raw Pyright JSON output to our structured format.

    Args:
        raw_output: Raw JSON from Pyright
        page: Page number for pagination
        page_size: Number of diagnostics per page

    Returns:
        Structured PyrightResult with pagination
    """
    # Extract summary
    raw_summary = raw_output.get("summary", {})
    summary = PyrightSummary(
        filesAnalyzed=raw_summary.get("filesAnalyzed", 0),
        errorCount=raw_summary.get("errorCount", 0),
        warningCount=raw_summary.get("warningCount", 0),
        informationCount=raw_summary.get("informationCount", 0),
        timeInSec=raw_summary.get("timeInSec", 0.0),
    )

    # Extract diagnostics
    diagnostics = []
    for diag in raw_output.get("generalDiagnostics", []):
        # Skip diagnostics without file association
        if not diag.get("file"):
            continue

        # Parse range
        raw_range = diag.get("range", {})
        diagnostic_range = DiagnosticRange(
            start=raw_range.get("start", {"line": 0, "character": 0}),
            end=raw_range.get("end", {"line": 0, "character": 0}),
        )

        # Create diagnostic
        diagnostics.append(
            Diagnostic(
                file=diag["file"],
                severity=diag.get("severity", "error"),
                message=diag.get("message", ""),
                rule=diag.get("rule"),
                range=diagnostic_range,
            )
        )

    # Apply pagination
    paginated_diagnostics, pagination_info = paginate_diagnostics(diagnostics, page, page_size)
    
    return PyrightResult(
        summary=summary,
        diagnostics=paginated_diagnostics,
        version=raw_output.get("version"),
        pagination=pagination_info,
    )


@mcp.tool()
async def check_python_types(
    ctx: Context,
    severity_level: str = "warning",
    ignore_patterns: Optional[list[str]] = None,
    page: int = 1,
    page_size: int = 50,
) -> PyrightResult:
    """
    Run Pyright type checking on Python files in /app/code.

    This tool analyzes Python code for type errors, providing detailed
    diagnostics about type mismatches, missing type hints, and other
    type-related issues.

    Args:
        severity_level: Minimum severity to report (error, warning, information)
        ignore_patterns: Additional glob patterns to ignore
        page: Page number for pagination (starts at 1)
        page_size: Number of diagnostics per page (default 50)
        ctx: MCP context for progress reporting

    Returns:
        Structured type checking results with diagnostics (paginated)
    """
    try:
        # Validate path
        target_path = Path("/app/code").resolve()
        if not target_path.exists():
            raise FileNotFoundError("Path not found: /app/code")

        # Report initial progress
        await ctx.info(f"Starting Pyright analysis on: {target_path}")

        project_path = str(target_path)

        # Find Python files for progress reporting
        await ctx.debug("Discovering Python files...")
        python_files = find_python_files(project_path, ignore_patterns)
        await ctx.info(f"Found {len(python_files)} Python files to analyze")

        # Run Pyright
        await ctx.report_progress(0.3, 1.0, "Running Pyright analysis...")
        raw_results = execute_pyright(project_path, severity_level)

        # Transform results
        await ctx.report_progress(0.8, 1.0, "Processing results...")
        result = transform_pyright_output(raw_results, page, page_size)

        # Report summary
        summary = result.summary
        pagination = result.pagination
        pagination_msg = ""
        if pagination:
            pagination_msg = f" - Page {pagination.current_page}/{pagination.total_pages} ({len(result.diagnostics)} of {pagination.total_diagnostics} diagnostics)"
        
        await ctx.info(
            f"Analysis complete: {summary.errorCount} errors, "
            f"{summary.warningCount} warnings, "
            f"{summary.informationCount} info messages "
            f"({summary.filesAnalyzed} files in {summary.timeInSec:.2f}s){pagination_msg}"
        )

        await ctx.report_progress(1.0, 1.0, "Complete")

        return result

    except Exception as e:
        await ctx.error(f"Type checking failed: {str(e)}")
        raise


@mcp.tool()
async def list_python_files(
    ctx: Context,
    ignore_patterns: Optional[list[str]] = None,
) -> list[str]:
    """
    List all Python files in /app/code that would be analyzed.

    Useful for understanding what files will be checked before
    running the full type analysis.

    Args:
        ignore_patterns: Additional glob patterns to ignore
        ctx: MCP context

    Returns:
        List of Python file paths
    """
    try:
        target_path = Path("/app/code").resolve()
        if not target_path.exists():
            raise FileNotFoundError("Path not found: /app/code")

        await ctx.info(f"Searching for Python files in: {target_path}")
        files = find_python_files(str(target_path), ignore_patterns)

        await ctx.info(f"Found {len(files)} Python files")
        return files

    except Exception as e:
        await ctx.error(f"Failed to list files: {str(e)}")
        raise
