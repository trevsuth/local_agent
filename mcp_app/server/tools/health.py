# mcp/server/tools/health.py
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

from fastmcp import FastMCP


def register_health_tool(mcp: FastMCP) -> None:
    """
    Register a simple health check tool.

    This is intentionally boring:
    - no DB access
    - no side effects
    - always returns quickly

    It is meant for:
    - smoke tests
    - docker healthchecks
    - n8n connectivity checks
    """

    @mcp.tool
    def health() -> dict:
        """
        Health check for the MCP server.

        Returns basic runtime information so callers can confirm:
        - the server is running
        - the correct environment is loaded
        """
        return {
            "status": "ok",
            "service": "mcp-demo",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "env": os.environ.get("MCP_ENV", "unknown"),
        }
