# Pagination Support for Pyright MCP Server

The Pyright MCP server now supports pagination to handle large responses that exceed MCP token limits (25,000 tokens).

## Overview

When analyzing large projects with many type errors, the response can exceed the maximum allowed tokens. Pagination breaks the diagnostics into smaller, manageable chunks.

## Usage

### Basic Usage

```python
# Get first page of diagnostics (default: 50 per page)
result = await check_python_types(
    ctx=ctx,
    severity_level="error"
)

# Check if there are more pages
if result.pagination.has_next_page:
    # Get next page
    next_result = await check_python_types(
        ctx=ctx,
        severity_level="error", 
        page=2
    )
```

### Custom Page Size

```python
# Get 100 diagnostics per page
result = await check_python_types(
    ctx=ctx,
    severity_level="error",
    page=1,
    page_size=100
)
```

### Navigation Pattern

```python
page = 1
all_diagnostics = []

while True:
    result = await check_python_types(
        ctx=ctx,
        severity_level="error",
        page=page,
        page_size=50
    )
    
    all_diagnostics.extend(result.diagnostics)
    
    if not result.pagination.has_next_page:
        break
        
    page += 1

print(f"Total diagnostics found: {len(all_diagnostics)}")
```

## Parameters

### `check_python_types` Parameters

- `ctx`: MCP context (required)
- `severity_level`: Minimum severity level (`"error"`, `"warning"`, `"information"`) - default: `"warning"`
- `ignore_patterns`: List of glob patterns to ignore - default: `None`
- `page`: Page number (1-based) - default: `1`
- `page_size`: Number of diagnostics per page - default: `50`

## Response Structure

The response now includes a `pagination` field:

```python
class PyrightResult:
    summary: PyrightSummary           # Analysis summary
    diagnostics: list[Diagnostic]     # Current page diagnostics  
    version: str                      # Pyright version
    pagination: PaginationInfo        # Pagination metadata

class PaginationInfo:
    current_page: int                 # Current page number
    total_pages: int                  # Total number of pages
    page_size: int                    # Items per page
    total_diagnostics: int            # Total diagnostic count
    has_next_page: bool               # True if more pages exist
    has_previous_page: bool           # True if previous pages exist
```

## Examples

### Example 1: Basic Error Checking with Pagination

```python
# Check for critical errors only, 25 per page
result = await check_python_types(
    ctx=ctx,
    severity_level="error",
    page=1,
    page_size=25
)

print(f"Page {result.pagination.current_page} of {result.pagination.total_pages}")
print(f"Showing {len(result.diagnostics)} of {result.pagination.total_diagnostics} errors")

for diagnostic in result.diagnostics:
    print(f"{diagnostic.file}:{diagnostic.range.start['line']} - {diagnostic.message}")
```

### Example 2: Processing All Pages

```python
async def get_all_diagnostics(ctx, severity_level="warning"):
    """Get all diagnostics across all pages."""
    all_diagnostics = []
    page = 1
    
    while True:
        result = await check_python_types(
            ctx=ctx,
            severity_level=severity_level,
            page=page,
            page_size=100  # Larger pages for efficiency
        )
        
        all_diagnostics.extend(result.diagnostics)
        
        print(f"Processed page {page}/{result.pagination.total_pages}")
        
        if not result.pagination.has_next_page:
            break
            
        page += 1
    
    return all_diagnostics

# Usage
all_errors = await get_all_diagnostics(ctx, "error")
print(f"Found {len(all_errors)} total errors")
```

### Example 3: Specific Page Access

```python
# Jump directly to page 5
result = await check_python_types(
    ctx=ctx,
    severity_level="warning",
    page=5,
    page_size=20
)

if result.pagination.current_page == 5:
    print("Successfully retrieved page 5")
    print(f"Showing diagnostics {(5-1)*20 + 1} to {(5-1)*20 + len(result.diagnostics)}")
```

## Best Practices

1. **Start with Default Settings**: Use default `page=1` and `page_size=50` for initial requests
2. **Adjust Page Size**: Increase `page_size` for efficiency if you need all results
3. **Check Pagination Info**: Always check `has_next_page` before requesting more pages
4. **Handle Edge Cases**: Pages beyond the total will return the last valid page
5. **Monitor Token Usage**: Larger page sizes may still hit token limits for very detailed diagnostics

## Error Handling

```python
try:
    result = await check_python_types(
        ctx=ctx,
        severity_level="error",
        page=999,  # Invalid page
        page_size=50
    )
    # Invalid page numbers are automatically clamped to valid range
    print(f"Returned page: {result.pagination.current_page}")
    
except Exception as e:
    print(f"Analysis failed: {e}")
```

## Migration from Previous Versions

Previous version:
```python
result = await check_python_types(ctx=ctx, severity_level="error")
# All diagnostics returned at once
```

New version (backwards compatible):
```python
result = await check_python_types(ctx=ctx, severity_level="error")
# Returns first page of diagnostics (50 by default)
# Access result.pagination to check for more pages
```

The API is fully backwards compatible - existing code will work unchanged but will receive paginated results by default.