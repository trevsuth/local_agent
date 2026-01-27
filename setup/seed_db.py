# setup/seed_db.py
"""
Seed the SQLite database with realistic US data using Faker.

Design goals:
- deterministic seeding via --rng-seed
- realistic addresses/phones/companies/titles
- BOM + inventory populated so availability/lead-time logic works
- optional forced shortages so "anticipated wait time" reliably triggers

Usage:
  pip install faker

  python setup/seed_db.py --db data/mcp_demo.sqlite --seed
  python setup/seed_db.py --db data/mcp_demo.sqlite --seed --users 100 --products 25 --suppliers 15 --components 60 --orders 120
  python setup/seed_db.py --db data/mcp_demo.sqlite --seed --force-shortage
"""

from __future__ import annotations

import argparse
import random
import sqlite3
from datetime import date, timedelta
from typing import Dict, List, Sequence, Tuple

from faker import Faker


PRODUCT_WORDS = [
    "Alpha",
    "Nova",
    "Orion",
    "Vertex",
    "Nimbus",
    "Apex",
    "Pulse",
    "Summit",
    "Ion",
    "Quanta",
]
PRODUCT_TYPES = [
    "Widget",
    "Gadget",
    "Module",
    "Device",
    "Assembly",
    "Kit",
    "Unit",
    "Pack",
]
COMPONENT_TYPES = [
    "Bolt",
    "Sensor",
    "Valve",
    "Motor",
    "Gear",
    "Relay",
    "Bearing",
    "Switch",
    "Bracket",
    "Housing",
]

LEAD_TIME_CHOICES = [0, 3, 5, 7, 10, 14, 21, 28]


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def _table_count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"])


def wipe_data(conn: sqlite3.Connection) -> None:
    # Order matters due to FKs
    tables = [
        "order_details",
        "order_headers",
        "bill_of_materials",
        "components",
        "products",
        "suppliers",
        "users",
        "audit_log",
    ]
    with conn:
        for t in tables:
            conn.execute(f"DELETE FROM {t}")
        # Reset autoincrement counters
        conn.execute("DELETE FROM sqlite_sequence")


def seed_users(conn: sqlite3.Connection, fake: Faker, n: int) -> None:
    rows: List[Tuple] = []
    for i in range(1, n + 1):
        rows.append(
            (
                i,
                fake.first_name(),
                fake.last_name(),
                fake.job(),
                fake.company(),
                fake.street_address(),
                fake.city(),
                fake.state_abbr(),
                fake.postcode(),
                fake.phone_number(),
            )
        )
    with conn:
        conn.executemany(
            """
            INSERT INTO users
              (id, first_name, last_name, title, company, address, city, state, zipcode, phone_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def seed_suppliers(conn: sqlite3.Connection, fake: Faker, n: int) -> None:
    rows: List[Tuple] = []
    for i in range(1, n + 1):
        rows.append(
            (
                i,
                f"{fake.company()} Components",
                fake.street_address(),
                fake.city(),
                fake.state_abbr(),
                fake.postcode(),
                fake.name(),
                fake.phone_number(),
            )
        )
    with conn:
        conn.executemany(
            """
            INSERT INTO suppliers
              (id, supplier_name, address, city, state, zipcode, contact_name, phone_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def seed_products(conn: sqlite3.Connection, n: int) -> None:
    rows: List[Tuple] = []
    used = set()
    i = 1
    while i <= n:
        name = f"{random.choice(PRODUCT_WORDS)} {random.choice(PRODUCT_TYPES)}"
        if name in used:
            continue
        used.add(name)
        price = round(random.uniform(25, 750), 2)
        rows.append((i, name, price))
        i += 1

    with conn:
        conn.executemany(
            "INSERT INTO products (id, product_name, price) VALUES (?, ?, ?)",
            rows,
        )


def seed_components(
    conn: sqlite3.Connection, fake: Faker, n: int, supplier_count: int
) -> None:
    rows: List[Tuple] = []
    for i in range(1, n + 1):
        supplier_id = random.randint(1, supplier_count)
        comp_name = f"{random.choice(COMPONENT_TYPES)}-{fake.bothify(text='##??')}"
        qoh = random.randint(0, 350)
        unit_cost = round(random.uniform(0.25, 120.0), 2)
        lead_time_days = random.choice(LEAD_TIME_CHOICES)
        reorder_point = random.randint(0, 50)
        rows.append(
            (i, supplier_id, comp_name, qoh, unit_cost, lead_time_days, reorder_point)
        )

    with conn:
        conn.executemany(
            """
            INSERT INTO components
              (id, supplier_id, component_name, quantity_on_hand, unit_cost, lead_time_days, reorder_point)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def seed_bom(
    conn: sqlite3.Connection, product_count: int, component_count: int
) -> None:
    # For each product, pick 3-8 components, each with qty 1-6
    rows: List[Tuple[int, int, int]] = []
    for pid in range(1, product_count + 1):
        k = random.randint(3, 8)
        component_ids = random.sample(range(1, component_count + 1), k=k)
        for cid in component_ids:
            qty = random.randint(1, 6)
            rows.append((pid, cid, qty))

    with conn:
        conn.executemany(
            """
            INSERT INTO bill_of_materials (product_id, component_id, component_qty)
            VALUES (?, ?, ?)
            """,
            rows,
        )


def seed_orders(
    conn: sqlite3.Connection,
    user_count: int,
    product_count: int,
    n_orders: int,
    fake: Faker,
) -> None:
    # Create DRAFT orders with details; order_total is maintained by triggers.
    headers: List[Tuple] = []
    details: List[Tuple] = []

    for _ in range(n_orders):
        user_id = random.randint(1, user_count)
        order_date = fake.date_between(start_date="-180d", end_date="today")
        headers.append((user_id, order_date.isoformat(), None, 0.0, "DRAFT"))

    with conn:
        cur = conn.executemany(
            """
            INSERT INTO order_headers (user_id, order_date, delivery_date, order_total, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            headers,
        )

        # We need the inserted order IDs. For simplicity, read them back:
        order_ids = [
            int(r["id"])
            for r in conn.execute(
                "SELECT id FROM order_headers ORDER BY id ASC"
            ).fetchall()
        ]
        if len(order_ids) < n_orders:
            order_ids = order_ids[-n_orders:]

        # Build details
        for oid in order_ids[-n_orders:]:
            line_count = random.randint(1, 6)
            product_ids = random.sample(
                range(1, product_count + 1), k=min(line_count, product_count)
            )
            for pid in product_ids:
                qty = random.randint(1, 10)
                price = float(
                    conn.execute(
                        "SELECT price FROM products WHERE id = ?", (pid,)
                    ).fetchone()["price"]
                )
                line_total = round(price * qty, 2)
                details.append((oid, pid, qty, price, line_total))

        conn.executemany(
            """
            INSERT INTO order_details (order_id, product_id, quantity, unit_price, line_total)
            VALUES (?, ?, ?, ?, ?)
            """,
            details,
        )


def force_shortage_scenario(
    conn: sqlite3.Connection, *, max_components_to_zero: int = 2
) -> None:
    """
    Ensure wait-time logic triggers by forcing a few components to have 0 on hand
    and a non-zero lead time.
    """
    rows = conn.execute(
        """
        SELECT id
        FROM components
        ORDER BY lead_time_days DESC, id ASC
        LIMIT ?
        """,
        (max_components_to_zero,),
    ).fetchall()

    if not rows:
        return

    with conn:
        for r in rows:
            conn.execute(
                "UPDATE components SET quantity_on_hand = 0, lead_time_days = MAX(lead_time_days, 14) WHERE id = ?",
                (int(r["id"]),),
            )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--db", required=True, help="Path to SQLite DB (e.g. data/mcp_demo.sqlite)"
    )
    p.add_argument(
        "--seed",
        action="store_true",
        help="Actually seed data (otherwise just sanity-check)",
    )
    p.add_argument(
        "--wipe", action="store_true", help="Delete existing data before seeding"
    )
    p.add_argument(
        "--rng-seed",
        type=int,
        default=42,
        help="Deterministic seed for repeatable demo data",
    )

    p.add_argument("--users", type=int, default=100)
    p.add_argument("--suppliers", type=int, default=15)
    p.add_argument("--products", type=int, default=25)
    p.add_argument("--components", type=int, default=60)
    p.add_argument("--orders", type=int, default=120)

    p.add_argument(
        "--force-shortage",
        action="store_true",
        help="Force at least one shortage for demo reliability",
    )
    args = p.parse_args()

    random.seed(args.rng_seed)
    fake = Faker("en_US")
    Faker.seed(args.rng_seed)

    conn = connect(args.db)
    try:
        if not args.seed:
            # quick sanity output
            for t in [
                "users",
                "suppliers",
                "products",
                "components",
                "bill_of_materials",
                "order_headers",
                "order_details",
                "audit_log",
            ]:
                try:
                    print(f"{t}: {_table_count(conn, t)}")
                except sqlite3.OperationalError:
                    print(f"{t}: (missing table) - did you run setup/create_db.py?")
            return

        if args.wipe:
            wipe_data(conn)

        # Seed in FK-safe order
        seed_users(conn, fake, args.users)
        seed_suppliers(conn, fake, args.suppliers)
        seed_products(conn, args.products)
        seed_components(conn, fake, args.components, args.suppliers)
        seed_bom(conn, args.products, args.components)
        seed_orders(conn, args.users, args.products, args.orders, fake)

        if args.force_shortage:
            force_shortage_scenario(conn)

        # Summary counts
        print(f"Seeded {args.db}")
        for t in [
            "users",
            "suppliers",
            "products",
            "components",
            "bill_of_materials",
            "order_headers",
            "order_details",
        ]:
            print(f"  {t}: {_table_count(conn, t)}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
