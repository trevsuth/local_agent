# MCP Tools

## health
Simple health check tool (no inputs).

Input:
- No parameters

Returns:
- `status` (string)
- `service` (string)
- `timestamp_utc` (string, ISO8601)
- `env` (string, `MCP_ENV` or `unknown`)

Example response:
```json
{
  "status": "ok",
  "service": "mcp-demo",
  "timestamp_utc": "2026-01-28T12:34:56.789+00:00",
  "env": "local"
}
```

## quote_inventory_availability
Quote whether an order can be fulfilled from current component inventory.

Input parameters:
- `payload` (string, required): JSON string with:
  - `lines` (array, required): list of `{ "product_id": int, "quantity": int }`
  - `handling_days` (number, optional; default 2)
  - `shipping_days` (number, optional; default 5)
- `db_path` (string, optional): override DB path; default uses `data/mcp_demo.sqlite`

Example tool input:
```json
{
  "payload": "{\"lines\":[{\"product_id\":1,\"quantity\":10}],\"handling_days\":2,\"shipping_days\":5}"
}
```

Returns:
- `can_fulfill_now` (boolean)
- `earliest_ship_date` (string, YYYY-MM-DD)
- `estimated_delivery_date` (string, YYYY-MM-DD)
- `bottleneck_components` (array):
  - `component_id` (int)
  - `component_name` (string)
  - `required_qty` (int)
  - `quantity_on_hand` (int)
  - `shortage` (int)
  - `lead_time_days` (int)
  - `available_on` (string, YYYY-MM-DD)
- `explanation` (string)

Example response:
```json
{
  "can_fulfill_now": false,
  "earliest_ship_date": "2026-02-05",
  "estimated_delivery_date": "2026-02-10",
  "bottleneck_components": [
    {
      "component_id": 7,
      "component_name": "Flux Capacitor",
      "required_qty": 10,
      "quantity_on_hand": 2,
      "shortage": 8,
      "lead_time_days": 5,
      "available_on": "2026-02-02"
    }
  ],
  "explanation": "Order is short on Flux Capacitor (need 10, have 2). Lead time is 5 days; earliest ship date is 2026-02-05."
}
```

## get_all_products
Return all products with the number of units buildable from parts on hand.

Input:
- No parameters

Returns:
- `products` (array):
  - `product_id` (int)
  - `product_name` (string)
  - `units_on_hand` (int)

Example response:
```json
{
  "products": [
    {"product_id": 1, "product_name": "Nova Widget", "units_on_hand": 12},
    {"product_id": 2, "product_name": "Vertex Device", "units_on_hand": 4}
  ]
}
```

## get_all_customers
Return all customers with order counts and total order value.

Input:
- No parameters

Returns:
- `customers` (array):
  - `customer_id` (int)
  - `name` (string)
  - `company` (string)
  - `orders_count` (int)
  - `total_order_value` (number)

Example response:
```json
{
  "customers": [
    {
      "customer_id": 1,
      "name": "Ada Lovelace",
      "company": "Analytical Engines Inc.",
      "orders_count": 3,
      "total_order_value": 1250.0
    }
  ]
}
```

## add_customer
Add a customer (writes to the users table).

Input:
- `first_name` (string, required)
- `last_name` (string, required)
- `title` (string, required)
- `company` (string, required)
- `address` (string, required)
- `city` (string, required)
- `state` (string, required)
- `zipcode` (string, required)
- `phone_number` (string, required)

Validation:
- Missing field → `Field <name> must be present.`
- Wrong type (cannot be coerced) → `Field <name> must be a <type>.`

Example response:
```json
{
  "customer": {
    "id": 26,
    "first_name": "Ada",
    "last_name": "Lovelace",
    "title": "Engineer",
    "company": "Analytical Engines Inc.",
    "address": "123 Example St",
    "city": "London",
    "state": "LN",
    "zipcode": "SW1A 1AA",
    "phone_number": "555-123-4567"
  }
}
```

## get_customer_by_id
Return a customer by id.

Input:
- `customer_id` (int, required)

Returns:
- `customer` (object) with full user fields
- If not found: `{ "error": "Customer <id> not found." }`

Example response:
```json
{
  "customer": {
    "id": 1,
    "first_name": "Ada",
    "last_name": "Lovelace",
    "title": "Engineer",
    "company": "Analytical Engines Inc.",
    "address": "123 Example St",
    "city": "London",
    "state": "LN",
    "zipcode": "SW1A 1AA",
    "phone_number": "555-123-4567"
  }
}
```
