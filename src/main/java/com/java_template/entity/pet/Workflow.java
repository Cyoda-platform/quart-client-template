package com.java_template.entity;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestTemplate;

import java.util.Random;
import java.util.concurrent.CompletableFuture;

import static com.java_template.common.config.Config.*;

public class Workflow {

    private static final Logger logger = LoggerFactory.getLogger(Workflow.class);
    private static final ObjectMapper mapper = new ObjectMapper();
    private static final RestTemplate restTemplate = new RestTemplate();

    // Workflow orchestration only here
    public CompletableFuture<ObjectNode> processpet(ObjectNode petNode) {
        if (!petNode.hasNonNull("id") || petNode.get("id").asLong(0L) == 0L) {
            long generatedId = new Random().nextLong() & Long.MAX_VALUE;
            petNode.put("id", generatedId);
            logger.debug("processpet: Generated new id {}", generatedId);
        }

        if (petNode.hasNonNull("id") && (!petNode.hasNonNull("name") || petNode.get("name").asText().isEmpty())) {
            return processFetchExternalData(petNode).thenCompose(fetchedNode -> {
                // no further orchestration here
                return CompletableFuture.completedFuture(fetchedNode);
            });
        }

        return CompletableFuture.completedFuture(petNode);
    }

    // Business logic only
    private CompletableFuture<ObjectNode> processFetchExternalData(ObjectNode petNode) {
        return CompletableFuture.supplyAsync(() -> {
            long petId = petNode.get("id").asLong();
            logger.debug("processFetchExternalData: Fetching external data for pet id {}", petId);
            try {
                String url = PETSTORE_API_BASE + "/pet/" + petId;
                String responseBody = restTemplate.getForObject(url, String.class);
                if (responseBody == null) {
                    logger.warn("processFetchExternalData: Empty response from external API for id {}", petId);
                    return petNode;
                }
                JsonNode extPetNode = mapper.readTree(responseBody);

                if (extPetNode.hasNonNull("name")) petNode.put("name", extPetNode.get("name").asText());
                if (extPetNode.hasNonNull("status")) petNode.put("status", extPetNode.get("status").asText());

                if (extPetNode.hasNonNull("category") && extPetNode.get("category").hasNonNull("name")) {
                    petNode.put("category", extPetNode.get("category").get("name").asText());
                }

                processAddAudit(petId);

                return petNode;
            } catch (Exception e) {
                logger.error("processFetchExternalData: Error fetching external pet data", e);
                return petNode;
            }
        });
    }

    // Business logic only: add audit asynchronously; no changes to current petNode
    private void processAddAudit(long petId) {
        CompletableFuture.runAsync(() -> {
            try {
                ObjectNode auditNode = mapper.createObjectNode();
                auditNode.put("petId", petId);
                auditNode.put("action", "fetched");
                auditNode.put("timestamp", System.currentTimeMillis());
                // TODO: replace with real addItem call to entityService for petAudit model
                logger.info("processAddAudit: audit entity created for petId {}", petId);
            } catch (Exception e) {
                logger.error("processAddAudit: Failed to create audit entity", e);
            }
        });
    }
}