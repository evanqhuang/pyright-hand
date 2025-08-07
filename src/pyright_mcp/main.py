"""Main entry point for Pyright MCP server."""

import argparse
import logging
import sys

from .server import mcp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Pyright-hand MCP Server - Python type checking for AI assistants"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level",
    )

    args = parser.parse_args()

    # Configure logging
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    try:
        # Run the server
        logger.info("Starting Pyright-hand MCP server with stdio transport")
        mcp.run(transport="stdio")

    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Server failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
