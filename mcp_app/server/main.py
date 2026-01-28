# mcp_app/server/main.py
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List

from fastmcp import FastMCP
from fastmcp.tools import FunctionTool

from mcp_app.server.db import db_session, get_db_path
from mcp_app.server.services.availability import (
    AvailabilityQuote,
    OrderLine,
    quote_availability,
)
from mcp_app.server.observability import setup_logging, setup_tracing, get_tracer
from mcp_app.server.tools.health import register_health_tool
from mcp_app.server.tools.products import register_products_tool
from mcp_app.server.tools.customers import register_customers_tool
from mcp_app.server.routes.health import register_health_route

# IMPORTANT: for stdio transport, don't print to stdout; log to stderr.
log = setup_logging("mcp-demo")
setup_tracing("mcp-demo")
tracer = get_tracer("mcp_app.server")

mcp = FastMCP("MCP Demo Server")
register_health_tool(mcp)
register_health_route(mcp)
register_products_tool(mcp)
register_customers_tool(mcp)


def quote_inventory_availability(
    payload: str,
    db_path: str = "",
) -> Dict[str, object]:
    """
    Quote whether an order can be fulfilled from current component inventory.

    Provide a list of line items (product_id + quantity). If components are short,
    returns the anticipated ship/delivery dates based on component lead times and
    includes the bottleneck components.
    """
    # Expect JSON payload to keep MCP input schema simple for clients.
    with tracer.start_as_current_span("quote_inventory_availability") as span:
        data = json.loads(payload)
        lines: List[Dict[str, float]] = data.get("lines", [])
        handling_days = float(data.get("handling_days", 2))
        shipping_days = float(data.get("shipping_days", 5))
        parsed_lines = [
            OrderLine(
                product_id=int(line["product_id"]),
                quantity=int(line["quantity"]),
            )
            for line in lines
        ]
        path: Path = get_db_path(db_path or None)
        log.info("quote_inventory_availability db=%s lines=%d", path, len(parsed_lines))

        span.set_attribute("db.path", str(path))
        span.set_attribute("order.lines", len(parsed_lines))
        span.set_attribute("order.handling_days", int(handling_days))
        span.set_attribute("order.shipping_days", int(shipping_days))

        with db_session(path) as conn:
            quote = quote_availability(
                conn,
                parsed_lines,
                handling_days=int(handling_days),
                shipping_days=int(shipping_days),
            )
        return quote.model_dump() if hasattr(quote, "model_dump") else quote.dict()


# Register tool with a simplified, explicit schema for client compatibility.
_quote_tool = FunctionTool.from_function(
    quote_inventory_availability,
    name="quote_inventory_availability",
    output_schema={"type": "object", "additionalProperties": True},
)
_quote_tool.parameters = {
    "type": "object",
    "required": ["payload"],
    "properties": {
        "payload": {"type": "string"},
        "db_path": {"type": "string", "default": ""},
    },
    "additionalProperties": False,
}
mcp.add_tool(_quote_tool)


if __name__ == "__main__":
    # Choose transport via env if you like; default is whatever FastMCP uses.
    # Common options: "stdio" for local tools; "http" for network use.
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    host = os.environ.get("MCP_HTTP_HOST", "127.0.0.1")
    port = int(os.environ.get("MCP_HTTP_PORT", "8000"))
    log.info("Starting MCP server transport=%s host=%s port=%s", transport, host, port)
    # Explicitly bind host/port so the container exposes the service outside itself.
    mcp.run(transport=transport, host=host, port=port)
