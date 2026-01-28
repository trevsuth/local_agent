# mcp_app/server/tools/customers.py
from __future__ import annotations

from typing import Dict, List

from fastmcp import FastMCP

from mcp_app.server.db import db_session, get_db_path
from mcp_app.server.observability import get_tracer


def register_customers_tool(mcp: FastMCP) -> None:
    """
    Register customer reporting tools.
    """

    @mcp.tool
    def get_all_customers() -> Dict[str, List[Dict[str, object]]]:
        """
        Return all customers with order counts and total order value.
        """
        tracer = get_tracer("mcp_app.server.customers")
        with tracer.start_as_current_span("get_all_customers"):
            path = get_db_path()
            sql = """
            SELECT
              u.id AS customer_id,
              u.first_name,
              u.last_name,
              u.company,
              COUNT(oh.id) AS orders_count,
              COALESCE(SUM(oh.order_total), 0) AS total_order_value
            FROM users u
            LEFT JOIN order_headers oh ON oh.user_id = u.id
            GROUP BY u.id, u.first_name, u.last_name, u.company
            ORDER BY u.id ASC
            """
            with db_session(path) as conn:
                rows = conn.execute(sql).fetchall()

            data = [
                {
                    "customer_id": int(r["customer_id"]),
                    "name": f'{r["first_name"]} {r["last_name"]}',
                    "company": str(r["company"]),
                    "orders_count": int(r["orders_count"]),
                    "total_order_value": float(r["total_order_value"]),
                }
                for r in rows
            ]
            return {"customers": data}
