# mcp_app/server/tools/products.py
from __future__ import annotations

from typing import Dict, List

from fastmcp import FastMCP

from mcp_app.server.db import db_session, get_db_path
from mcp_app.server.observability import get_tracer


def register_products_tool(mcp: FastMCP) -> None:
    """
    Register product inventory summary tools.
    """

    @mcp.tool
    def get_all_products() -> Dict[str, List[Dict[str, object]]]:
        """
        Return all products with the number of units buildable from parts on hand.
        """
        tracer = get_tracer("mcp_app.server.products")
        with tracer.start_as_current_span("get_all_products"):
            path = get_db_path()
            sql = """
            SELECT
              p.id AS product_id,
              p.product_name,
              CASE
                WHEN COUNT(bom.component_id) = 0 THEN 0
                ELSE MIN(CAST(c.quantity_on_hand / bom.component_qty AS INTEGER))
              END AS units_on_hand
            FROM products p
            LEFT JOIN bill_of_materials bom ON bom.product_id = p.id
            LEFT JOIN components c ON c.id = bom.component_id
            GROUP BY p.id, p.product_name
            ORDER BY p.id ASC
            """
            with db_session(path) as conn:
                rows = conn.execute(sql).fetchall()

            data = [
                {
                    "product_id": int(r["product_id"]),
                    "product_name": str(r["product_name"]),
                    "units_on_hand": int(r["units_on_hand"]),
                }
                for r in rows
            ]
            return {"products": data}
