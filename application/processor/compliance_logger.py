"""
ComplianceLogger processor for institutional trading platform.

Immutable audit log writer for orders/executions/actions.
Attached to transitions: all order and execution state changes (ASYNC_SAME_TX).
"""

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from common.processor.base import CyodaEntity, CyodaProcessor


class ComplianceLogger(CyodaProcessor):
    """
    Writes immutable audit logs for all order and execution events.
    """

    def __init__(self) -> None:
        super().__init__(
            name="ComplianceLogger",
            description="Writes immutable audit logs for compliance",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Log the entity state change to audit trail.

        Args:
            entity: The entity being transitioned
            **kwargs: Additional logging parameters (transition_name, from_state, to_state)

        Returns:
            The entity unchanged
        """
        try:
            entity_id = getattr(entity, "technical_id", None)
            self.logger.info(f"Logging audit trail for {entity_id}")

            # Create audit log entry
            audit_entry = self._create_audit_entry(entity, **kwargs)

            # Write to immutable log
            await self._write_audit_log(audit_entry)

            # Store audit reference on entity
            if not hasattr(entity, "auditMetadata"):
                setattr(entity, "auditMetadata", {})
            audit_metadata = getattr(entity, "auditMetadata")
            audit_metadata["last_audit_id"] = audit_entry["audit_id"]
            audit_metadata["last_audit_timestamp"] = audit_entry["timestamp"]

            self.logger.info(f"Audit log entry created: {audit_entry['audit_id']}")
            return entity

        except Exception as e:
            self.logger.error(f"Error writing audit log: {str(e)}")
            raise

    def _create_audit_entry(self, entity: CyodaEntity, **kwargs: Any) -> Dict[str, Any]:
        """
        Create an audit log entry for the entity state change.

        Args:
            entity: The entity being logged
            **kwargs: Additional context (transition_name, from_state, to_state, user, etc.)

        Returns:
            Audit entry dictionary
        """
        entity_id = getattr(entity, "technical_id", None)
        entity_type = getattr(entity, "entity_type", "unknown")
        current_state = getattr(entity, "state", None)

        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        audit_id = str(uuid.uuid4())

        # Extract transition context
        transition_name = kwargs.get("transition_name", "unknown")
        from_state = kwargs.get("from_state", None)
        to_state = kwargs.get("to_state", current_state)
        user = kwargs.get("user", "SYSTEM")
        source = kwargs.get("source", "API")

        # Create audit entry
        audit_entry: Dict[str, Any] = {
            "audit_id": audit_id,
            "timestamp": timestamp,
            "entity_id": entity_id,
            "entity_type": entity_type,
            "transition": transition_name,
            "from_state": from_state,
            "to_state": to_state,
            "user": user,
            "source": source,
            "entity_snapshot": self._create_entity_snapshot(entity),
        }

        # Create hash for immutability verification
        audit_entry["hash"] = self._create_audit_hash(audit_entry)

        return audit_entry

    def _create_entity_snapshot(self, entity: CyodaEntity) -> Dict[str, Any]:
        """
        Create a snapshot of the entity state for audit trail.

        Args:
            entity: The entity to snapshot

        Returns:
            Entity snapshot dictionary
        """
        snapshot: Dict[str, Any] = {
            "technical_id": getattr(entity, "technical_id", None),
            "entity_id": getattr(entity, "entity_id", None),
            "state": getattr(entity, "state", None),
        }

        # Include key business fields based on entity type
        entity_type = getattr(entity, "entity_type", None)

        if entity_type == "order":
            snapshot.update(
                {
                    "accountId": getattr(entity, "accountId", None),
                    "instrumentId": getattr(entity, "instrumentId", None),
                    "side": getattr(entity, "side", None),
                    "quantity": getattr(entity, "quantity", None),
                    "price": getattr(entity, "price", None),
                }
            )
        elif entity_type == "execution":
            snapshot.update(
                {
                    "orderId": getattr(entity, "orderId", None),
                    "executionId": getattr(entity, "executionId", None),
                    "quantity": getattr(entity, "quantity", None),
                    "price": getattr(entity, "price", None),
                    "venue": getattr(entity, "venue", None),
                }
            )

        return snapshot

    def _create_audit_hash(self, audit_entry: Dict[str, Any]) -> str:
        """
        Create a hash of the audit entry for immutability verification.

        Args:
            audit_entry: The audit entry to hash

        Returns:
            SHA256 hash of the entry
        """
        # Create a deterministic string representation
        entry_str = (
            f"{audit_entry['audit_id']}"
            f"{audit_entry['timestamp']}"
            f"{audit_entry['entity_id']}"
            f"{audit_entry['entity_type']}"
            f"{audit_entry['transition']}"
            f"{audit_entry['from_state']}"
            f"{audit_entry['to_state']}"
        )

        return hashlib.sha256(entry_str.encode()).hexdigest()

    async def _write_audit_log(self, audit_entry: Dict[str, Any]) -> None:
        """
        Write the audit entry to immutable storage.

        Args:
            audit_entry: The audit entry to write
        """
        # TODO: Implement immutable audit log storage
        # - Write to append-only log file
        # - Write to blockchain/ledger (optional)
        # - Write to compliance database
        # - Implement log rotation and archival
        # - Ensure tamper-evident logging

        self.logger.info(
            f"Audit entry {audit_entry['audit_id']}: "
            f"{audit_entry['entity_type']} {audit_entry['entity_id']} "
            f"{audit_entry['from_state']} -> {audit_entry['to_state']}"
        )
