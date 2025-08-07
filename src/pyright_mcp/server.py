"""MCP server implementation for Pyright."""

import logging
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import Context, FastMCP

from .file_finder import find_python_files
from .models import Diagnostic, DiagnosticRange, PyrightResult, PyrightSummary
from .pyright_runner import execute_pyright

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the MCP server
mcp = FastMCP("Pyright-hand Python Checker")


def transform_pyright_output(raw_output: dict) -> PyrightResult:
    """
    Transform raw Pyright JSON output to our structured format.

    Args:
        raw_output: Raw JSON from Pyright

    Returns:
        Structured PyrightResult
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

    return PyrightResult(
        summary=summary,
        diagnostics=diagnostics,
        version=raw_output.get("version"),
    )


@mcp.tool()
async def check_python_types(
    ctx: Context,
    severity_level: str = "warning",
    ignore_patterns: Optional[list[str]] = None,
) -> PyrightResult:
    """
    Run Pyright type checking on Python files in /app/code.

    This tool analyzes Python code for type errors, providing detailed
    diagnostics about type mismatches, missing type hints, and other
    type-related issues.

    Args:
        severity_level: Minimum severity to report (error, warning, information)
        ignore_patterns: Additional glob patterns to ignore
        ctx: MCP context for progress reporting

    Returns:
        Structured type checking results with diagnostics
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
        result = transform_pyright_output(raw_results)

        # Report summary
        summary = result.summary
        await ctx.info(
            f"Analysis complete: {summary.errorCount} errors, "
            f"{summary.warningCount} warnings, "
            f"{summary.informationCount} info messages "
            f"({summary.filesAnalyzed} files in {summary.timeInSec:.2f}s)"
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
