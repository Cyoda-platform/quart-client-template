package com.java_template.entity;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import lombok.extern.slf4j.Slf4j;

import java.util.concurrent.CompletableFuture;

@Slf4j
public class EntityWorkflowProcessor {

    private final ObjectMapper objectMapper = new ObjectMapper();

    // Workflow orchestration only here
    public CompletableFuture<ObjectNode> processPet(ObjectNode entity) {
        return processSetDefaultStatus(entity)
                .thenCompose(this::processAsyncLogName)
                .thenCompose(this::processAdditionalTasks);
    }

    // Sets default status if missing or empty
    private CompletableFuture<ObjectNode> processSetDefaultStatus(ObjectNode entity) {
        JsonNode statusNode = entity.get("status");
        if (statusNode == null || statusNode.asText().isBlank()) {
            entity.put("status", "available");
        }
        return CompletableFuture.completedFuture(entity);
    }

    // Example async fire-and-forget task logging pet name if present
    private CompletableFuture<ObjectNode> processAsyncLogName(ObjectNode entity) {
        CompletableFuture.runAsync(() -> {
            String petName = entity.hasNonNull("name") ? entity.get("name").asText() : "unknown";
            logger.info("Async workflow task: Pet name is '{}'", petName);
        });
        return CompletableFuture.completedFuture(entity);
    }

    // Placeholder for other async tasks, e.g., fetching related entities
    private CompletableFuture<ObjectNode> processAdditionalTasks(ObjectNode entity) {
        // TODO: add further workflow steps here if needed
        return CompletableFuture.completedFuture(entity);
    }
}