import logging
from datetime import datetime, timezone
from typing import Any

from application.entity.order import Order
from application.entity.shipment import Shipment
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from services.services import get_entity_service


class CreateOrderFromPaidProcessor(CyodaProcessor):
    def __init__(self) -> None:
        super().__init__(
            name="CreateOrderFromPaidProcessor",
            description="Creates order from paid cart, decrements stock, creates shipment",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        try:
            self.logger.info(
                f"Creating order from paid cart {getattr(entity, 'technical_id', '<unknown>')}"
            )

            order = cast_entity(entity, Order)
            entity_service = get_entity_service()

            timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            for line in order.lines:
                sku = line.get("sku")
                qty = line.get("qty", 0)

                if sku:
                    try:
                        product_result = await entity_service.find_by_business_id(
                            entity_class="Product",
                            business_id=sku,
                            business_id_field="sku",
                            entity_version="1",
                        )

                        if product_result:
                            product_data = product_result.data.model_dump(by_alias=True)
                            product_data["quantityAvailable"] = max(
                                0, product_data.get("quantityAvailable", 0) - qty
                            )

                            await entity_service.update(
                                entity_id=product_result.metadata.id,
                                entity=product_data,
                                entity_class="Product",
                                entity_version="1",
                            )

                            self.logger.info(
                                f"Decremented stock for product {sku} by {qty}"
                            )
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to decrement stock for {sku}: {str(e)}"
                        )

            shipment = Shipment(
                shipmentId=order.orderId,
                orderId=order.orderId,
                status="PICKING",
                lines=order.lines,
                createdAt=timestamp,
                updatedAt=timestamp,
            )

            shipment_data = shipment.model_dump(by_alias=True)

            await entity_service.save(
                entity=shipment_data,
                entity_class=Shipment.ENTITY_NAME,
                entity_version=str(Shipment.ENTITY_VERSION),
            )

            self.logger.info(
                f"Order {order.technical_id} created with shipment {shipment.shipmentId}"
            )

            return order

        except Exception as e:
            self.logger.error(
                f"Error creating order {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise
