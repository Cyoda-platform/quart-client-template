package com.java_template.entity;

import com.fasterxml.jackson.databind.node.ObjectNode;
import com.java_template.common.service.EntityService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Arrays;
import java.util.List;
import java.util.concurrent.CompletableFuture;

public class CyodaEntityControllerPrototype {

    private static final Logger logger = LoggerFactory.getLogger(CyodaEntityControllerPrototype.class);
    private final EntityService entityService;
    private static final String ENTITY_NAME = "Pet";
    private static final String ENTITY_VERSION = "1.0";

    private final List<String> petFacts = Arrays.asList(
            "Cats sleep for 70% of their lives.",
            "Dogs have three eyelids.",
            "A group of cats is called a clowder.",
            "Rabbits can see behind them without turning their heads."
    );

    public CyodaEntityControllerPrototype(EntityService entityService) {
        this.entityService = entityService;
    }

    // Workflow orchestration only
    private CompletableFuture<ObjectNode> processPet(Object entity) {
        return processValidateAndDefaultStatus(entity)
                .thenCompose(this::processAddAuditEntity)
                .thenApply(petNode -> {
                    logger.info("Finished processing pet entity");
                    return petNode;
                });
    }

    // Validate and default status if missing or invalid
    private CompletableFuture<ObjectNode> processValidateAndDefaultStatus(Object entity) {
        return CompletableFuture.supplyAsync(() -> {
            if (!(entity instanceof ObjectNode)) {
                logger.warn("Entity passed to processValidateAndDefaultStatus is not an ObjectNode");
                return (ObjectNode) entity;
            }
            ObjectNode petNode = (ObjectNode) entity;
            String status = petNode.path("status").asText(null);
            if (status == null || status.isEmpty() || !isValidStatus(status)) {
                petNode.put("status", "available");
                logger.debug("Defaulted pet status to 'available'");
            }
            logger.info("Validated pet status: {}", petNode.get("status").asText());
            return petNode;
        });
    }

    // Add supplementary PetAudit entity (fire-and-forget)
    private CompletableFuture<ObjectNode> processAddAuditEntity(Object entity) {
        if (!(entity instanceof ObjectNode)) {
            logger.warn("Entity passed to processAddAuditEntity is not an ObjectNode");
            return CompletableFuture.completedFuture((ObjectNode) entity);
        }
        ObjectNode petNode = (ObjectNode) entity;
        ObjectNode auditEntity = petNode.deepCopy();
        auditEntity.put("auditTimestamp", System.currentTimeMillis());
        auditEntity.put("auditAction", "ADD_OR_UPDATE");

        // Fire-and-forget supplementary entity add
        entityService.addItem("PetAudit", ENTITY_VERSION, auditEntity, e -> CompletableFuture.completedFuture((ObjectNode) e))
                .exceptionally(ex -> {
                    logger.error("Failed to add PetAudit entity", ex);
                    return null;
                });

        return CompletableFuture.completedFuture(petNode);
    }

    // Example status validation helper
    private boolean isValidStatus(String status) {
        return status.equalsIgnoreCase("available") ||
               status.equalsIgnoreCase("pending") ||
               status.equalsIgnoreCase("sold");
    }
}