```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, List

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory "databases"
products_db = {
    "p1": {
        "id": "p1",
        "name": "Sample Product 1",
        "description": "Description of product 1",
        "price": 19.99,
        "availability": 100,
        "image_url": "https://via.placeholder.com/150"
    },
    "p2": {
        "id": "p2",
        "name": "Sample Product 2",
        "description": "Description of product 2",
        "price": 29.99,
        "availability": 50,
        "image_url": "https://via.placeholder.com/150"
    }
}

inventory_db = {
    "p1": 100,
    "p2": 50
}

orders_db: Dict[str, Dict] = {}
customers_db: Dict[str, Dict] = {}
sessions: Dict[str, str] = {}  # token -> customer_id
promotions_db = {
    "PROMO10": 0.10,
    "PROMO20": 0.20
}

entity_jobs = {}

# Simple id generators
def generate_id(prefix: str) -> str:
    return f"{prefix}{int(datetime.utcnow().timestamp() * 1000)}"


# --- Product Catalog ---

@app.route('/products', methods=['GET'])
async def get_products():
    category = request.args.get('category')
    prod_id = request.args.get('id')
    # For simplicity, category ignored; prod_id filtered
    if prod_id:
        product = products_db.get(prod_id)
        if not product:
            return jsonify({"error": "Product not found"}), 404
        return jsonify({"products": [product]})
    return jsonify({"products": list(products_db.values())})


@app.route('/products/search', methods=['POST'])
async def post_products_search():
    data = await request.get_json()
    query = data.get("query", "").lower()
    filters = data.get("filters", {})
    price_min = filters.get("price_min", 0)
    price_max = filters.get("price_max", float('inf'))
    in_stock = filters.get("in_stock", None)

    # TODO: Implement external search API integration here.
    # For prototype, search local products by name and price range.
    filtered = []
    for p in products_db.values():
        if query and query not in p["name"].lower() and query not in p["description"].lower():
            continue
        if not (price_min <= p["price"] <= price_max):
            continue
        if in_stock is True and inventory_db.get(p["id"], 0) <= 0:
            continue
        filtered.append(p)
    return jsonify({"products": filtered})


# --- Inventory Management ---

@app.route('/inventory/<product_id>', methods=['GET'])
async def get_inventory(product_id):
    stock = inventory_db.get(product_id)
    if stock is None:
        return jsonify({"error": "Product not found"}), 404
    return jsonify({"product_id": product_id, "stock": stock})


@app.route('/inventory/update', methods=['POST'])
async def post_inventory_update():
    data = await request.get_json()
    product_id = data.get("product_id")
    adjustment = data.get("adjustment")
    if product_id not in inventory_db:
        return jsonify({"error": "Product not found"}), 404
    if not isinstance(adjustment, int):
        return jsonify({"error": "Invalid adjustment"}), 400

    # Update inventory locally
    inventory_db[product_id] += adjustment
    new_stock = inventory_db[product_id]

    # TODO: Sync with external ERP system (e.g. NetSuite/Odoo) here using httpx.AsyncClient

    return jsonify({"product_id": product_id, "new_stock": new_stock})


# --- Customer Accounts ---

@app.route('/customers/register', methods=['POST'])
async def post_customers_register():
    data = await request.get_json()
    email = data.get("email")
    password = data.get("password")
    name = data.get("name")

    if not (email and password and name):
        return jsonify({"error": "Missing fields"}), 400
    if email in customers_db:
        return jsonify({"error": "Email already registered"}), 400

    customer_id = generate_id("cus_")
    customers_db[email] = {"customer_id": customer_id, "email": email, "password": password, "name": name}
    return jsonify({"customer_id": customer_id, "message": "Registration successful"})


@app.route('/customers/login', methods=['POST'])
async def post_customers_login():
    data = await request.get_json()
    email = data.get("email")
    password = data.get("password")
    customer = customers_db.get(email)
    if not customer or customer["password"] != password:
        return jsonify({"error": "Invalid credentials"}), 401
    token = generate_id("tok_")
    sessions[token] = customer["customer_id"]
    return jsonify({"token": token, "customer_id": customer["customer_id"]})


@app.route('/customers/<customer_id>/orders', methods=['GET'])
async def get_customer_orders(customer_id):
    # Simple auth check by token query param (not secure, just prototype)
    token = request.args.get("token")
    if not token or sessions.get(token) != customer_id:
        return jsonify({"error": "Unauthorized"}), 403

    orders = [o for o in orders_db.values() if o["customer_id"] == customer_id]
    summary = []
    for o in orders:
        summary.append({
            "order_id": o["order_id"],
            "status": o["status"],
            "total": o["total"],
            "order_date": o["created_at"].isoformat()
        })
    return jsonify({"orders": summary})


# --- Order Processing ---

@app.route('/orders/create', methods=['POST'])
async def post_orders_create():
    data = await request.get_json()
    customer_id = data.get("customer_id")
    items = data.get("items", [])
    payment_method = data.get("payment_method")
    promo_code = data.get("promo_code")

    if not (customer_id and items and payment_method):
        return jsonify({"error": "Missing fields"}), 400
    if customer_id not in [c["customer_id"] for c in customers_db.values()]:
        return jsonify({"error": "Invalid customer"}), 400

    # Check stock availability
    for item in items:
        pid = item.get("product_id")
        qty = item.get("quantity", 0)
        if pid not in inventory_db or inventory_db[pid] < qty:
            return jsonify({"error": f"Insufficient stock for product {pid}"}), 400

    order_id = generate_id("ord_")
    total = 0.0
    for item in items:
        p = products_db.get(item["product_id"])
        if p:
            total += p["price"] * item["quantity"]

    discount = 0.0
    if promo_code:
        promo = promotions_db.get(promo_code.upper())
        if promo:
            discount = total * promo
            total -= discount

    order = {
        "order_id": order_id,
        "customer_id": customer_id,
        "items": items,
        "total": round(total, 2),
        "discount": round(discount, 2),
        "status": "Pending",
        "payment_status": "Pending",
        "shipping_status": "Pending",
        "promo_code": promo_code,
        "created_at": datetime.utcnow()
    }
    orders_db[order_id] = order

    # Fire and forget payment processing task
    entity_jobs[order_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    asyncio.create_task(process_order_payment(order_id, payment_method))

    return jsonify({"order_id": order_id, "status": "Pending"})


async def process_order_payment(order_id: str, payment_method: str):
    try:
        order = orders_db.get(order_id)
        if not order:
            logger.error(f"Order {order_id} not found for payment processing")
            return

        # Simulate payment via Stripe public API (use Stripe test API)
        # TODO: Replace with real payment gateway integration with secret keys
        async with httpx.AsyncClient() as client:
            # Stripe test: https://stripe.com/docs/api/charges/create?lang=curl
            # Using stripe's test endpoint to create a charge is not possible without keys,
            # so we simulate a successful payment here.

            # Simulate delay
            await asyncio.sleep(1)

        # On payment success
        order["status"] = "Paid"
        order["payment_status"] = "Succeeded"

        # Reserve stock locally
        for item in order["items"]:
            pid = item["product_id"]
            qty = item["quantity"]
            inventory_db[pid] -= qty

        # TODO: Notify ERP system about reserved stock

        # Schedule shipment task
        asyncio.create_task(schedule_shipment(order_id))

        entity_jobs[order_id]["status"] = "completed"
    except Exception as e:
        logger.exception(e)
        entity_jobs[order_id]["status"] = "failed"


async def schedule_shipment(order_id: str):
    try:
        order = orders_db.get(order_id)
        if not order:
            logger.error(f"Order {order_id} not found for shipment scheduling")
            return

        # TODO: Integrate with real shipping provider API (Royal Mail etc)
        # Placeholder: simulate shipment scheduling
        await asyncio.sleep(1)

        order["shipping_status"] = "Shipped"
        order["status"] = "Shipped"

        # TODO: Notify customer via email or notification system

    except Exception as e:
        logger.exception(e)


@app.route('/orders/<order_id>', methods=['GET'])
async def get_order(order_id):
    order = orders_db.get(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404
    return jsonify({
        "order_id": order["order_id"],
        "status": order["status"],
        "items": order["items"],
        "total": order["total"],
        "payment_status": order["payment_status"],
        "shipping_status": order["shipping_status"]
    })


@app.route('/orders/payment', methods=['POST'])
async def post_orders_payment():
    data = await request.get_json()
    order_id = data.get("order_id")
    payment_method = data.get("payment_method")

    if not order_id or not payment_method:
        return jsonify({"error": "Missing fields"}), 400
    order = orders_db.get(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404
    if order["payment_status"] == "Succeeded":
        return jsonify({"message": "Payment already succeeded", "order_id": order_id, "payment_status": "Succeeded"})

    entity_jobs[order_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    asyncio.create_task(process_order_payment(order_id, payment_method))
    return jsonify({"order_id": order_id, "payment_status": "Processing"})


@app.route('/orders/cancel', methods=['POST'])
async def post_orders_cancel():
    data = await request.get_json()
    order_id = data.get("order_id")
    reason = data.get("reason", "")

    if not order_id:
        return jsonify({"error": "Missing order_id"}), 400
    order = orders_db.get(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404
    if order["status"] in ("Shipped", "Completed", "Canceled"):
        return jsonify({"error": f"Cannot cancel order in status {order['status']}"}), 400

    order["status"] = "Canceled"
    order["payment_status"] = "Canceled"
    # TODO: Implement refund processing if payment succeeded

    # Return stock
    for item in order["items"]:
        pid = item["product_id"]
        qty = item["quantity"]
        inventory_db[pid] += qty

    return jsonify({"order_id": order_id, "status": "Canceled"})


# --- Promotions & Discounts ---

@app.route('/promotions/apply', methods=['POST'])
async def post_promotions_apply():
    data = await request.get_json()
    order_id = data.get("order_id")
    promo_code = data.get("promo_code")

    if not order_id or not promo_code:
        return jsonify({"error": "Missing fields"}), 400
    order = orders_db.get(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404

    promo = promotions_db.get(promo_code.upper())
    if not promo:
        return jsonify({"error": "Invalid promo code"}), 400

    discount_amount = round(order["total"] * promo, 2)
    new_total = round(order["total"] - discount_amount, 2)
    order["discount"] = discount_amount
    order["total"] = new_total
    order["promo_code"] = promo_code.upper()

    return jsonify({"order_id": order_id, "discount_amount": discount_amount, "new_total": new_total})


if __name__ == '__main__':
    import sys
    import logging

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```