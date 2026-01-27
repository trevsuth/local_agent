-- setup/schema.sql
-- SQLite schema for MCP demo (orders + BOM + inventory + audit)

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- Clean up triggers if re-running schema against an existing DB
DROP TRIGGER IF EXISTS trg_order_details_total_ins;
DROP TRIGGER IF EXISTS trg_order_details_total_upd;
DROP TRIGGER IF EXISTS trg_order_details_total_del;

-- =========================
-- Audit log
-- =========================
CREATE TABLE IF NOT EXISTS audit_log (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  ts_utc        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  actor_user_id INTEGER NULL,
  source        TEXT NOT NULL,               -- e.g. 'mcp', 'n8n', 'db_trigger'
  action        TEXT NOT NULL,               -- domain action string
  entity_type   TEXT NOT NULL,               -- table or domain object
  entity_id     TEXT NULL,
  details_json  TEXT NULL
);

-- =========================
-- Core entities
-- =========================
CREATE TABLE IF NOT EXISTS users (
  id           INTEGER PRIMARY KEY,
  first_name   TEXT NOT NULL,
  last_name    TEXT NOT NULL,
  title        TEXT NOT NULL,
  company      TEXT NOT NULL,
  address      TEXT NOT NULL,
  city         TEXT NOT NULL,
  state        TEXT NOT NULL,
  zipcode      TEXT NOT NULL,
  phone_number TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS suppliers (
  id            INTEGER PRIMARY KEY,
  supplier_name TEXT NOT NULL,
  address       TEXT NOT NULL,
  city          TEXT NOT NULL,
  state         TEXT NOT NULL,
  zipcode       TEXT NOT NULL,
  contact_name  TEXT NOT NULL,
  phone_number  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
  id           INTEGER PRIMARY KEY,
  product_name TEXT NOT NULL UNIQUE,
  price        REAL NOT NULL CHECK (price >= 0)
);

CREATE TABLE IF NOT EXISTS components (
  id               INTEGER PRIMARY KEY,
  supplier_id      INTEGER NOT NULL,
  component_name   TEXT NOT NULL,
  quantity_on_hand INTEGER NOT NULL DEFAULT 0 CHECK (quantity_on_hand >= 0),
  unit_cost        REAL NOT NULL DEFAULT 0 CHECK (unit_cost >= 0),

  -- New columns for wait-time estimation + simple inventory policy demos
  lead_time_days   INTEGER NOT NULL DEFAULT 7 CHECK (lead_time_days >= 0),
  reorder_point    INTEGER NOT NULL DEFAULT 0 CHECK (reorder_point >= 0),

  FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE RESTRICT
);

-- Bill of Materials (BOM): components required per product
CREATE TABLE IF NOT EXISTS bill_of_materials (
  product_id    INTEGER NOT NULL,
  component_id  INTEGER NOT NULL,
  component_qty INTEGER NOT NULL DEFAULT 1 CHECK (component_qty > 0),
  PRIMARY KEY (product_id, component_id),
  FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
  FOREIGN KEY (component_id) REFERENCES components(id) ON DELETE RESTRICT
);

-- Orders
CREATE TABLE IF NOT EXISTS order_headers (
  id            INTEGER PRIMARY KEY,
  user_id       INTEGER NOT NULL,
  order_date    TEXT NOT NULL,               -- YYYY-MM-DD
  delivery_date TEXT NULL,                   -- may be NULL until submit/quote
  order_total   REAL NOT NULL DEFAULT 0 CHECK (order_total >= 0),

  status        TEXT NOT NULL DEFAULT 'DRAFT'
                CHECK (status IN ('DRAFT','SUBMITTED','BACKORDERED','CANCELLED','SHIPPED')),

  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS order_details (
  id          INTEGER PRIMARY KEY,
  order_id    INTEGER NOT NULL,
  product_id  INTEGER NOT NULL,
  quantity    INTEGER NOT NULL CHECK (quantity > 0),
  unit_price  REAL NOT NULL CHECK (unit_price >= 0),   -- snapshot
  line_total  REAL NOT NULL CHECK (line_total >= 0),   -- unit_price * quantity
  FOREIGN KEY (order_id) REFERENCES order_headers(id) ON DELETE CASCADE,
  FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT
);

-- =========================
-- Indexes
-- =========================
CREATE INDEX IF NOT EXISTS idx_order_headers_user_id   ON order_headers(user_id);
CREATE INDEX IF NOT EXISTS idx_order_headers_status    ON order_headers(status);
CREATE INDEX IF NOT EXISTS idx_order_details_order_id  ON order_details(order_id);
CREATE INDEX IF NOT EXISTS idx_order_details_product_id ON order_details(product_id);
CREATE INDEX IF NOT EXISTS idx_components_supplier_id  ON components(supplier_id);
CREATE INDEX IF NOT EXISTS idx_bom_component_id        ON bill_of_materials(component_id);

-- =========================
-- Triggers: keep order_total correct
-- =========================
CREATE TRIGGER trg_order_details_total_ins
AFTER INSERT ON order_details
BEGIN
  UPDATE order_headers
    SET order_total = (
      SELECT COALESCE(SUM(line_total), 0)
      FROM order_details
      WHERE order_id = NEW.order_id
    )
  WHERE id = NEW.order_id;
END;

CREATE TRIGGER trg_order_details_total_upd
AFTER UPDATE ON order_details
BEGIN
  UPDATE order_headers
    SET order_total = (
      SELECT COALESCE(SUM(line_total), 0)
      FROM order_details
      WHERE order_id = NEW.order_id
    )
  WHERE id = NEW.order_id;

  UPDATE order_headers
    SET order_total = (
      SELECT COALESCE(SUM(line_total), 0)
      FROM order_details
      WHERE order_id = OLD.order_id
    )
  WHERE id = OLD.order_id;
END;

CREATE TRIGGER trg_order_details_total_del
AFTER DELETE ON order_details
BEGIN
  UPDATE order_headers
    SET order_total = (
      SELECT COALESCE(SUM(line_total), 0)
      FROM order_details
      WHERE order_id = OLD.order_id
    )
  WHERE id = OLD.order_id;
END;
