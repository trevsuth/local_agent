# mcp/server/services/availability.py
from __future__ import annotations

from datetime import date, timedelta
from typing import List, Optional, Sequence, Tuple

import sqlite3
from pydantic import BaseModel, Field


class OrderLine(BaseModel):
    product_id: int = Field(..., ge=1)
    quantity: int = Field(..., ge=1)


class BottleneckComponent(BaseModel):
    component_id: int
    component_name: str
    required_qty: int
    quantity_on_hand: int
    shortage: int
    lead_time_days: int
    available_on: str  # YYYY-MM-DD


class AvailabilityQuote(BaseModel):
    can_fulfill_now: bool
    earliest_ship_date: str  # YYYY-MM-DD
    estimated_delivery_date: str  # YYYY-MM-DD
    bottleneck_components: List[BottleneckComponent]
    explanation: str


def _iso(d: date) -> str:
    return d.isoformat()


def _values_cte(lines: Sequence[OrderLine]) -> Tuple[str, List[int]]:
    """
    Builds:
      WITH cart(product_id, qty) AS (VALUES (?, ?), (?, ?), ...)
    Returns (cte_sql, params).
    """
    placeholders = ", ".join(["(?, ?)"] * len(lines))
    cte = f"WITH cart(product_id, qty) AS (VALUES {placeholders})"
    params: List[int] = []
    for ln in lines:
        params.extend([ln.product_id, ln.quantity])
    return cte, params


def quote_availability(
    conn: sqlite3.Connection,
    lines: Sequence[OrderLine],
    *,
    handling_days: int = 2,
    shipping_days: int = 5,
    today: Optional[date] = None,
) -> AvailabilityQuote:
    """
    Computes whether an order can be built from component inventory.
    If shortages exist, returns an anticipated ship/delivery estimate based on lead times.
    """
    if not lines:
        raise ValueError("lines must not be empty")

    today = today or date.today()

    cart_cte, params = _values_cte(lines)

    sql = f"""
    {cart_cte},
    required AS (
      SELECT
        bom.component_id,
        SUM(cart.qty * bom.component_qty) AS required_qty
      FROM cart
      JOIN bill_of_materials bom ON bom.product_id = cart.product_id
      GROUP BY bom.component_id
    )
    SELECT
      r.component_id,
      c.component_name,
      CAST(r.required_qty AS INTEGER) AS required_qty,
      c.quantity_on_hand,
      CASE
        WHEN (r.required_qty - c.quantity_on_hand) > 0 THEN CAST(r.required_qty - c.quantity_on_hand AS INTEGER)
        ELSE 0
      END AS shortage,
      c.lead_time_days
    FROM required r
    JOIN components c ON c.id = r.component_id
    ORDER BY shortage DESC, c.lead_time_days DESC, c.id ASC
    """

    rows = conn.execute(sql, params).fetchall()

    # If a product has no BOM entries, this returns empty; treat as "buildable now" for demo simplicity.
    if not rows:
        ship = today + timedelta(days=handling_days)
        delivery = ship + timedelta(days=shipping_days)
        return AvailabilityQuote(
            can_fulfill_now=True,
            earliest_ship_date=_iso(ship),
            estimated_delivery_date=_iso(delivery),
            bottleneck_components=[],
            explanation="No BOM rows found for the requested products; assuming buildable now.",
        )

    bottlenecks: List[BottleneckComponent] = []
    max_lead = 0

    for r in rows:
        shortage = int(r["shortage"])
        if shortage > 0:
            lead = int(r["lead_time_days"])
            max_lead = max(max_lead, lead)
            available_on = today + timedelta(days=lead)
            bottlenecks.append(
                BottleneckComponent(
                    component_id=int(r["component_id"]),
                    component_name=str(r["component_name"]),
                    required_qty=int(r["required_qty"]),
                    quantity_on_hand=int(r["quantity_on_hand"]),
                    shortage=shortage,
                    lead_time_days=lead,
                    available_on=_iso(available_on),
                )
            )

    if not bottlenecks:
        ship = today + timedelta(days=handling_days)
        delivery = ship + timedelta(days=shipping_days)
        return AvailabilityQuote(
            can_fulfill_now=True,
            earliest_ship_date=_iso(ship),
            estimated_delivery_date=_iso(delivery),
            bottleneck_components=[],
            explanation="All required components are available on hand; the order can be fulfilled now.",
        )

    # Earliest ship date is constrained by the slowest shortage component
    ship = (today + timedelta(days=max_lead)) + timedelta(days=handling_days)
    delivery = ship + timedelta(days=shipping_days)

    top = bottlenecks[0]
    if len(bottlenecks) == 1:
        explanation = (
            f"Order is short on {top.component_name} (need {top.required_qty}, have {top.quantity_on_hand}). "
            f"Lead time is {top.lead_time_days} days; earliest ship date is {_iso(ship)}."
        )
    else:
        explanation = (
            f"Order cannot be fulfilled immediately; {len(bottlenecks)} components are short. "
            f"The bottleneck is {top.component_name} (short {top.shortage}, lead {top.lead_time_days} days), "
            f"so earliest ship date is {_iso(ship)}."
        )

    return AvailabilityQuote(
        can_fulfill_now=False,
        earliest_ship_date=_iso(ship),
        estimated_delivery_date=_iso(delivery),
        bottleneck_components=bottlenecks,
        explanation=explanation,
    )
