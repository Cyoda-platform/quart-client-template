import logging
from typing import Any, Dict, Optional

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate_querystring

from application.entity.product import Product
from common.service.entity_service import SearchConditionRequest, SearchOperator
from services.services import get_entity_service

logger = logging.getLogger(__name__)

ui_products_bp = Blueprint("ui_products", __name__, url_prefix="/ui/products")


@ui_products_bp.route("", methods=["GET"])
@tag(["products"])
@operation_id("list_products")
async def list_products() -> ResponseReturnValue:
    """List products with search, category, and price filters"""
    try:
        search = request.args.get("search", "").strip()
        category = request.args.get("category", "").strip()
        min_price_str = request.args.get("minPrice", "")
        max_price_str = request.args.get("maxPrice", "")
        page = int(request.args.get("page", "0"))
        page_size = int(request.args.get("pageSize", "20"))

        service = get_entity_service()

        builder = SearchConditionRequest.builder()

        if category:
            builder.equals("category", category)

        if search:
            builder.contains("name", search)
            builder.contains("description", search)

        if min_price_str:
            try:
                min_price = float(min_price_str)
                builder.add_condition(
                    "price", SearchOperator.GREATER_OR_EQUAL, min_price
                )
            except ValueError:
                pass

        if max_price_str:
            try:
                max_price = float(max_price_str)
                builder.add_condition("price", SearchOperator.LESS_OR_EQUAL, max_price)
            except ValueError:
                pass

        condition = builder.build()

        results = await service.search(
            entity_class=Product.ENTITY_NAME,
            condition=condition,
            entity_version=str(Product.ENTITY_VERSION),
        )

        products = []
        for result in results:
            product_data = result.data.model_dump(by_alias=True)
            slim_product = {
                "sku": product_data.get("sku"),
                "name": product_data.get("name"),
                "description": product_data.get("description"),
                "price": product_data.get("price"),
                "quantityAvailable": product_data.get("quantityAvailable"),
                "category": product_data.get("category"),
                "imageUrl": None,
            }
            if product_data.get("media"):
                for media in product_data["media"]:
                    if media.get("type") == "image":
                        slim_product["imageUrl"] = media.get("url")
                        break

            products.append(slim_product)

        start = page * page_size
        end = start + page_size
        paginated = products[start:end]

        return (
            jsonify(
                {
                    "products": paginated,
                    "total": len(products),
                    "page": page,
                    "pageSize": page_size,
                }
            ),
            200,
        )

    except Exception as e:
        logger.exception("Error listing products: %s", str(e))
        return jsonify({"error": str(e)}), 500


@ui_products_bp.route("/<sku>", methods=["GET"])
@tag(["products"])
@operation_id("get_product_by_sku")
async def get_product_by_sku(sku: str) -> ResponseReturnValue:
    """Get full product document by SKU"""
    try:
        service = get_entity_service()

        result = await service.find_by_business_id(
            entity_class=Product.ENTITY_NAME,
            business_id=sku,
            business_id_field="sku",
            entity_version=str(Product.ENTITY_VERSION),
        )

        if not result:
            return jsonify({"error": "Product not found"}), 404

        product_data = result.data.model_dump(by_alias=True)
        return jsonify(product_data), 200

    except Exception as e:
        logger.exception("Error getting product %s: %s", sku, str(e))
        return jsonify({"error": str(e)}), 500
