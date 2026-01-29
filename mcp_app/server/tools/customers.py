# mcp_app/server/tools/customers.py
from __future__ import annotations

from typing import Dict, List

from fastmcp import FastMCP
from fastmcp.tools import FunctionTool

from mcp_app.server.db import db_session, get_db_path
from mcp_app.server.observability import get_tracer

_REQUIRED_FIELDS = {
    "first_name": str,
    "last_name": str,
    "title": str,
    "company": str,
    "address": str,
    "city": str,
    "state": str,
    "zipcode": str,
    "phone_number": str,
}


def _coerce_value(name: str, value: object, expected: type) -> str | None:
    if value is None:
        return None
    if isinstance(value, expected):
        return value
    if expected is str and isinstance(value, (int, float, bool)):
        return str(value)
    return None


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

    def add_customer(
        first_name: object | None = None,
        last_name: object | None = None,
        title: object | None = None,
        company: object | None = None,
        address: object | None = None,
        city: object | None = None,
        state: object | None = None,
        zipcode: object | None = None,
        phone_number: object | None = None,
    ) -> Dict[str, object]:
        """
        Insert a customer into the users table.
        """
        tracer = get_tracer("mcp_app.server.customers")
        with tracer.start_as_current_span("add_customer"):
            payload: Dict[str, object] = {
                "first_name": first_name,
                "last_name": last_name,
                "title": title,
                "company": company,
                "address": address,
                "city": city,
                "state": state,
                "zipcode": zipcode,
                "phone_number": phone_number,
            }
            coerced: Dict[str, str] = {}
            for field, expected in _REQUIRED_FIELDS.items():
                if payload.get(field) is None:
                    return {"error": f"Field {field} must be present."}
                value = _coerce_value(field, payload.get(field), expected)
                if value is None:
                    return {"error": f"Field {field} must be a {expected.__name__}."}
                coerced[field] = value

            path = get_db_path()
            with db_session(path) as conn:
                cur = conn.execute(
                    """
                    INSERT INTO users
                      (first_name, last_name, title, company, address, city, state, zipcode, phone_number)
                    VALUES
                      (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        coerced["first_name"],
                        coerced["last_name"],
                        coerced["title"],
                        coerced["company"],
                        coerced["address"],
                        coerced["city"],
                        coerced["state"],
                        coerced["zipcode"],
                        coerced["phone_number"],
                    ),
                )
                conn.commit()
                row_id = cur.lastrowid
                row = conn.execute(
                    """
                    SELECT id, first_name, last_name, title, company, address, city, state, zipcode, phone_number
                    FROM users
                    WHERE id = ?
                    """,
                    (row_id,),
                ).fetchone()

            return {
                "customer": {
                    "id": int(row["id"]),
                    "first_name": str(row["first_name"]),
                    "last_name": str(row["last_name"]),
                    "title": str(row["title"]),
                    "company": str(row["company"]),
                    "address": str(row["address"]),
                    "city": str(row["city"]),
                    "state": str(row["state"]),
                    "zipcode": str(row["zipcode"]),
                    "phone_number": str(row["phone_number"]),
                }
            }

    _add_tool = FunctionTool.from_function(
        add_customer,
        name="add_customer",
        output_schema={"type": "object", "additionalProperties": True},
    )
    _add_tool.parameters = {
        "type": "object",
        "required": [
            "first_name",
            "last_name",
            "title",
            "company",
            "address",
            "city",
            "state",
            "zipcode",
            "phone_number",
        ],
        "properties": {
            "first_name": {"type": "string"},
            "last_name": {"type": "string"},
            "title": {"type": "string"},
            "company": {"type": "string"},
            "address": {"type": "string"},
            "city": {"type": "string"},
            "state": {"type": "string"},
            "zipcode": {"type": "string"},
            "phone_number": {"type": "string"},
        },
        "additionalProperties": False,
    }
    mcp.add_tool(_add_tool)

    def get_customer_by_id(customer_id: object | None = None) -> Dict[str, object]:
        """
        Return a single customer by id.
        """
        tracer = get_tracer("mcp_app.server.customers")
        with tracer.start_as_current_span("get_customer_by_id"):
            if customer_id is None:
                return {"error": "Field customer_id must be present."}
            try:
                cid = int(customer_id)
            except (TypeError, ValueError):
                return {"error": "Field customer_id must be a int."}

            path = get_db_path()
            with db_session(path) as conn:
                row = conn.execute(
                    """
                    SELECT id, first_name, last_name, title, company, address, city, state, zipcode, phone_number
                    FROM users
                    WHERE id = ?
                    """,
                    (cid,),
                ).fetchone()

            if row is None:
                return {"error": f"Customer {cid} not found."}

            return {
                "customer": {
                    "id": int(row["id"]),
                    "first_name": str(row["first_name"]),
                    "last_name": str(row["last_name"]),
                    "title": str(row["title"]),
                    "company": str(row["company"]),
                    "address": str(row["address"]),
                    "city": str(row["city"]),
                    "state": str(row["state"]),
                    "zipcode": str(row["zipcode"]),
                    "phone_number": str(row["phone_number"]),
                }
            }

    _get_by_id_tool = FunctionTool.from_function(
        get_customer_by_id,
        name="get_customer_by_id",
        output_schema={"type": "object", "additionalProperties": True},
    )
    _get_by_id_tool.parameters = {
        "type": "object",
        "required": ["customer_id"],
        "properties": {"customer_id": {"type": "number"}},
        "additionalProperties": False,
    }
    mcp.add_tool(_get_by_id_tool)
