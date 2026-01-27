# mcp_app/server/main.py
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

from fastmcp import FastMCP

from mcp_app.server.db import db_session, get_db_path
from mcp_app.server.services.availability import (
    AvailabilityQuote,
    OrderLine,
    quote_availability,
)
from mcp_app.server.tools.health import register_health_tool
from mcp_app.server.routes.health import register_health_route

# IMPORTANT: for stdio transport, don't print to stdout; log to stderr.
logging.basicConfig(stream=sys.stderr, level=os.environ.get("LOG_LEVEL", "INFO"))
log = logging.getLogger("mcp-demo")

mcp = FastMCP("MCP Demo Server")
register_health_tool(mcp)
register_health_route(mcp)


@mcp.tool
def quote_inventory_availability(
    lines: List[OrderLine],
    handling_days: int = 2,
    shipping_days: int = 5,
    db_path: Optional[str] = None,
) -> AvailabilityQuote:
    """
    Quote whether an order can be fulfilled from current component inventory.

    Provide a list of line items (product_id + quantity). If components are short,
    returns the anticipated ship/delivery dates based on component lead times and
    includes the bottleneck components.
    """
    path: Path = get_db_path(db_path)
    log.info("quote_inventory_availability db=%s lines=%d", path, len(lines))

    with db_session(path) as conn:
        return quote_availability(
            conn,
            lines,
            handling_days=handling_days,
            shipping_days=shipping_days,
        )


if __name__ == "__main__":
    # Choose transport via env if you like; default is whatever FastMCP uses.
    # Common options: "stdio" for local tools; "http" for network use.
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    host = os.environ.get("MCP_HTTP_HOST", "127.0.0.1")
    port = int(os.environ.get("MCP_HTTP_PORT", "8000"))
    log.info("Starting MCP server transport=%s host=%s port=%s", transport, host, port)
    # Explicitly bind host/port so the container exposes the service outside itself.
    mcp.run(transport=transport, host=host, port=port)
