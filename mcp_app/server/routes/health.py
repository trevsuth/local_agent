from __future__ import annotations

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse


def register_health_route(mcp: FastMCP) -> None:
    """
    Simple HTTP health endpoint for infrastructure checks.
    """

    @mcp.custom_route("/health", methods=["GET"])
    def health_route(request: Request):  # request is required by Starlette
        return JSONResponse(
            {
                "status": "ok",
                "service": "mcp-demo",
            }
        )
