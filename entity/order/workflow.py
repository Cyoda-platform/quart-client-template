from fastapi import HTTPException
import asyncio

async def async_calculate_order_totals(entity: dict):
    # Business logic to calculate totals
    total = 0
    for item in entity.get('items', []):
        price = item.get('price', 0)
        quantity = item.get('quantity', 1)
        total += price * quantity
    entity['total'] = total

async def async_fetch_product_details(product_id):
    # Placeholder for async fetching product details
    # TODO: Replace with real async call to product service
    await asyncio.sleep(0.1)  # Simulate network delay
    return {"name": f"Product {product_id}", "price": 10.0}

async def enrich_items_with_product_details(entity: dict):
    items = entity.get('items', [])
    if items and isinstance(items, list):
        for item in items:
            product_id = item.get('product_id')
            if product_id is not None:
                product_details = await async_fetch_product_details(product_id)
                item.setdefault('name', product_details.get('name'))
                item.setdefault('price', product_details.get('price'))

async def process_order(entity: dict):
    # Workflow orchestration only, no business logic here
    await async_calculate_order_totals(entity)
    await enrich_items_with_product_details(entity)