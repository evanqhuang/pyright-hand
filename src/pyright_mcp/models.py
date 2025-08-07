"""Data models for Pyright MCP server."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class DiagnosticRange(BaseModel):
    """Range in source code."""

    start: dict[str, int]
    end: dict[str, int]


class Diagnostic(BaseModel):
    """Single diagnostic from Pyright."""

    file: str
    severity: str
    message: str
    rule: Optional[str] = None
    range: DiagnosticRange


class PyrightSummary(BaseModel):
    """Summary statistics from Pyright analysis."""

    filesAnalyzed: int = Field(default=0)
    errorCount: int = Field(default=0)
    warningCount: int = Field(default=0)
    informationCount: int = Field(default=0)
    timeInSec: float = Field(default=0.0)


class PyrightResult(BaseModel):
    """Complete result from Pyright analysis."""

    summary: PyrightSummary
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    version: Optional[str] = None