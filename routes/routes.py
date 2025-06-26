from fastapi import FastAPI, Request, HTTPException
from typing import Dict, Any
import asyncio

app = FastAPI()

# Simulated in-memory entity storage
entity_storage = {
    'user': [],
    'order': [],
    'product': []
}

# Simulated entity service with add, update, delete operations
class EntityService:
    async def add(self, entity_model: str, entity: Dict[str, Any]):
        entity_storage[entity_model].append(entity)

    async def update(self, entity_model: str, entity_id: Any, updated_entity: Dict[str, Any]):
        for idx, ent in enumerate(entity_storage[entity_model]):
            if ent.get('id') == entity_id:
                entity_storage[entity_model][idx] = updated_entity
                return
        raise HTTPException(status_code=404, detail=f"{entity_model} not found")

    async def delete(self, entity_model: str, entity_id: Any):
        for idx, ent in enumerate(entity_storage[entity_model]):
            if ent.get('id') == entity_id:
                del entity_storage[entity_model][idx]
                return
        raise HTTPException(status_code=404, detail=f"{entity_model} not found")

entity_service = EntityService()

# Simulated async functions representing external calls or fire and forget tasks
async def async_fetch_profile(user_id):
    await asyncio.sleep(0.1)  # simulate IO delay
    return {"bio": "User bio for user_id " + str(user_id)}

async def async_send_welcome_email(user_email):
    await asyncio.sleep(0.1)  # simulate sending email
    # fire and forget simulated by no return

async def async_calculate_order_totals(order):
    await asyncio.sleep(0.1)  # simulate calculation
    # example total calculation
    order['total'] = sum(item.get('price', 0) * item.get('quantity', 1) for item in order.get('items', []))

async def async_fetch_product_details(product_id):
    await asyncio.sleep(0.1)  # simulate product lookup
    return {"name": f"Product {product_id}", "price": 10.0 * product_id}

# Workflow functions

async def process_user(entity: dict):
    # Enrich user profile asynchronously before persistence
    if 'id' in entity:
        entity['profile'] = await async_fetch_profile(entity['id'])
    # Fire and forget welcome email if new user (assumed no 'created' flag means new)
    if not entity.get('created'):
        # Cannot call entity_service inside workflow, so just trigger async task here (await to ensure execution)
        await async_send_welcome_email(entity.get('email', ''))
        entity['created'] = True  # mark as created to prevent repeat email

async def process_order(entity: dict):
    # Calculate totals asynchronously before persistence
    await async_calculate_order_totals(entity)
    # Enrich each item with product details
    items = entity.get('items', [])
    if items and isinstance(items, list):
        for item in items:
            product_id = item.get('product_id')
            if product_id is not None:
                product_details = await async_fetch_product_details(product_id)
                # Add product name and price to item if not present
                item.setdefault('name', product_details.get('name'))
                item.setdefault('price', product_details.get('price'))

async def process_product(entity: dict):
    # No async logic currently for products, placeholder for extension
    pass

# Endpoints

@app.post("/users")
async def create_user(request: Request):
    user_data = await request.json()
    # Validate minimal required fields
    if 'id' not in user_data or 'email' not in user_data:
        raise HTTPException(status_code=400, detail="User must have 'id' and 'email'")
    # Call workflow function before persistence
    await process_user(user_data)
    await entity_service.add('user', user_data)
    return {"status": "user created", "user": user_data}

@app.put("/users/{user_id}")
async def update_user(user_id: int, request: Request):
    user_data = await request.json()
    user_data['id'] = user_id
    # Call workflow function before persistence
    await process_user(user_data)
    await entity_service.update('user', user_id, user_data)
    return {"status": "user updated", "user": user_data}

@app.post("/orders")
async def create_order(request: Request):
    order_data = await request.json()
    if 'id' not in order_data:
        raise HTTPException(status_code=400, detail="Order must have 'id'")
    if 'items' not in order_data or not isinstance(order_data['items'], list):
        raise HTTPException(status_code=400, detail="Order must have 'items' as a list")
    await process_order(order_data)
    await entity_service.add('order', order_data)
    return {"status": "order created", "order": order_data}

@app.put("/orders/{order_id}")
async def update_order(order_id: int, request: Request):
    order_data = await request.json()
    order_data['id'] = order_id
    await process_order(order_data)
    await entity_service.update('order', order_id, order_data)
    return {"status": "order updated", "order": order_data}

@app.post("/products")
async def create_product(request: Request):
    product_data = await request.json()
    if 'id' not in product_data:
        raise HTTPException(status_code=400, detail="Product must have 'id'")
    await process_product(product_data)
    await entity_service.add('product', product_data)
    return {"status": "product created", "product": product_data}

@app.put("/products/{product_id}")
async def update_product(product_id: int, request: Request):
    product_data = await request.json()
    product_data['id'] = product_id
    await process_product(product_data)
    await entity_service.update('product', product_id, product_data)
    return {"status": "product updated", "product": product_data}

@app.delete("/users/{user_id}")
async def delete_user(user_id: int):
    await entity_service.delete('user', user_id)
    return {"status": "user deleted", "user_id": user_id}

@app.delete("/orders/{order_id}")
async def delete_order(order_id: int):
    await entity_service.delete('order', order_id)
    return {"status": "order deleted", "order_id": order_id}

@app.delete("/products/{product_id}")
async def delete_product(product_id: int):
    await entity_service.delete('product', product_id)
    return {"status": "product deleted", "product_id": product_id}