package com.java_template.entity;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.java_template.common.service.EntityService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.MediaType;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.server.ResponseStatusException;

import java.util.*;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;

import static com.java_template.common.config.Config.*;

@Validated
@RestController
@RequestMapping("/cyoda-pets")
public class CyodaEntityControllerPrototype {

    private static final Logger logger = LoggerFactory.getLogger(CyodaEntityControllerPrototype.class);
    private final RestTemplate restTemplate = new RestTemplate();
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final EntityService entityService;
    private static final String ENTITY_NAME = "Pet";
    private final List<String> petFacts = Arrays.asList(
            "Cats sleep for 70% of their lives.",
            "Dogs have three eyelids.",
            "A group of cats is called a clowder.",
            "Rabbits can see behind them without turning their heads."
    );
    private static final String PETSTORE_API_BASE = "https://petstore.swagger.io/v2";

    public CyodaEntityControllerPrototype(EntityService entityService) {
        this.entityService = entityService;
    }

    @PostMapping(value = "/fetch", consumes = MediaType.APPLICATION_JSON_VALUE, produces = MediaType.APPLICATION_JSON_VALUE)
    public Map<String, Object> fetchPets(@Valid @RequestBody(required = false) FetchFilter filter) throws ExecutionException, InterruptedException {
        logger.info("Fetching pets with filter {}", filter);
        String statusFilter = filter != null ? filter.getStatus() : "";
        String url = PETSTORE_API_BASE + "/pet/findByStatus?status=" + statusFilter;
        String json = restTemplate.getForObject(url, String.class);
        JsonNode root;
        try {
            root = objectMapper.readTree(json);
        } catch (Exception e) {
            logger.error("Error parsing JSON from petstore", e);
            throw new ResponseStatusException(org.springframework.http.HttpStatus.BAD_GATEWAY, "Unexpected format");
        }
        if (!root.isArray()) {
            throw new ResponseStatusException(org.springframework.http.HttpStatus.BAD_GATEWAY, "Unexpected format");
        }

        List<CompletableFuture<UUID>> addFutures = new ArrayList<>();
        int count = 0;
        for (JsonNode node : root) {
            long id = node.path("id").asLong(-1);
            if (id < 0) continue;
            ObjectNode petNode = objectMapper.createObjectNode();
            petNode.put("id", id);
            petNode.put("name", node.path("name").asText("Unnamed"));
            petNode.put("status", node.path("status").asText("unknown"));
            petNode.put("type", node.path("category").path("name").asText("Unknown"));
            // Add pet with workflow processing
            addFutures.add(entityService.addItem(ENTITY_NAME, ENTITY_VERSION, petNode, this::processPet));
            count++;
        }
        // Wait for all additions to complete
        for (CompletableFuture<UUID> future : addFutures) {
            future.get();
        }
        Map<String, Object> resp = new HashMap<>();
        resp.put("message", "Pets data fetched and updated successfully");
        resp.put("count", count);
        return resp;
    }

    @GetMapping(produces = MediaType.APPLICATION_JSON_VALUE)
    public List<Pet> listPets(@RequestParam(required = false) @Pattern(regexp = "available|pending|sold", message = "Invalid status") String status) throws ExecutionException, InterruptedException {
        logger.info("Listing pets with status {}", status);
        CompletableFuture<ArrayNode> itemsFuture;
        if (status == null || status.isEmpty()) {
            itemsFuture = entityService.getItems(ENTITY_NAME, ENTITY_VERSION);
        } else {
            String condition = String.format("status='%s'", status);
            itemsFuture = entityService.getItemsByCondition(ENTITY_NAME, ENTITY_VERSION, condition);
        }
        ArrayNode items = itemsFuture.get();
        List<Pet> result = new ArrayList<>();
        for (JsonNode item : items) {
            long technicalId = item.path("technicalId").asLong(-1);
            if (technicalId < 0) continue;
            String name = item.path("name").asText("Unnamed");
            String type = item.path("type").asText("Unknown");
            String petStatus = item.path("status").asText("unknown");
            if (status == null || status.isEmpty() || status.equalsIgnoreCase(petStatus)) {
                result.add(new Pet(technicalId, name, type, petStatus));
            }
        }
        return result;
    }

    // Workflow function to process Pet entity before persistence
    private CompletableFuture<ObjectNode> processPet(Object entity) {
        return CompletableFuture.supplyAsync(() -> {
            if (!(entity instanceof ObjectNode)) {
                logger.warn("Entity passed to processPet is not an ObjectNode");
                return (ObjectNode) entity;
            }
            ObjectNode petNode = (ObjectNode) entity;

            // Validate and default status
            String status = petNode.path("status").asText(null);
            if (status == null || status.isEmpty() || !isValidStatus(status)) {
                petNode.put("status", "available");
                logger.debug("Defaulted pet status to 'available'");
            }

            // Log the processing
            logger.info("Processing pet entity before persistence: {}", petNode);

            // Example: add supplementary entity of different entityModel "PetAudit"
            try {
                ObjectNode auditEntity = petNode.deepCopy();
                auditEntity.put("auditTimestamp", System.currentTimeMillis());
                auditEntity.put("auditAction", "ADD_OR_UPDATE");
                entityService.addItem("PetAudit", ENTITY_VERSION, auditEntity, e -> CompletableFuture.completedFuture((ObjectNode) e))
                        .exceptionally(ex -> {
                            logger.error("Failed to add PetAudit entity", ex);
                            return null;
                        });
            } catch (Exception ex) {
                logger.error("Exception during supplementary entity add in workflow", ex);
            }

            return petNode;
        });
    }

    @PostMapping(consumes = MediaType.APPLICATION_JSON_VALUE, produces = MediaType.APPLICATION_JSON_VALUE)
    public Map<String, Object> addPet(@Valid @RequestBody PetCreateRequest req) throws ExecutionException, InterruptedException {
        logger.info("Adding pet {}", req);
        ObjectNode petNode = objectMapper.createObjectNode();
        petNode.put("name", req.getName());
        petNode.put("type", req.getType());
        if (req.getStatus() != null && !req.getStatus().isEmpty()) {
            petNode.put("status", req.getStatus());
        }
        // Add pet entity with workflow processing
        CompletableFuture<UUID> idFuture = entityService.addItem(ENTITY_NAME, ENTITY_VERSION, petNode, this::processPet);
        UUID technicalId = idFuture.get();
        Map<String, Object> resp = new HashMap<>();
        resp.put("id", technicalId.toString());
        resp.put("message", "New pet added successfully");
        return resp;
    }

    @PostMapping(value = "/{id}/status", consumes = MediaType.APPLICATION_JSON_VALUE, produces = MediaType.APPLICATION_JSON_VALUE)
    public Map<String, Object> updatePetStatus(@PathVariable String id, @Valid @RequestBody StatusUpdateRequest req) throws ExecutionException, InterruptedException {
        logger.info("Updating status for pet {} to {}", id, req.getStatus());
        UUID technicalId;
        try {
            technicalId = UUID.fromString(id);
        } catch (IllegalArgumentException e) {
            throw new ResponseStatusException(org.springframework.http.HttpStatus.BAD_REQUEST, "Invalid pet id format");
        }
        CompletableFuture<ObjectNode> itemFuture = entityService.getItem(ENTITY_NAME, ENTITY_VERSION, technicalId);
        ObjectNode existingItem = itemFuture.get();
        if (existingItem == null || existingItem.isEmpty()) {
            throw new ResponseStatusException(org.springframework.http.HttpStatus.NOT_FOUND, "Pet not found");
        }
        // Update status directly on ObjectNode
        existingItem.put("status", req.getStatus());

        // Update entity with workflow processing
        CompletableFuture<UUID> updatedItemId = entityService.updateItem(ENTITY_NAME, ENTITY_VERSION, technicalId, existingItem, this::processPet);
        updatedItemId.get();

        Map<String, Object> resp = new HashMap<>();
        resp.put("id", id);
        resp.put("message", "Pet status updated successfully");
        return resp;
    }

    @GetMapping(value = "/fun/fact", produces = MediaType.APPLICATION_JSON_VALUE)
    public Map<String, String> randomPetFact() {
        String fact = petFacts.get(new Random().nextInt(petFacts.size()));
        logger.info("Random pet fact: {}", fact);
        return Collections.singletonMap("fact", fact);
    }

    private boolean isValidStatus(String status) {
        return "available".equalsIgnoreCase(status) || "pending".equalsIgnoreCase(status) || "sold".equalsIgnoreCase(status);
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class FetchFilter {
        @Pattern(regexp = "available|pending|sold", message = "Invalid status")
        private String status;
    }

    @Data
    public static class PetCreateRequest {
        @NotBlank
        @Size(min = 1, max = 100)
        private String name;
        @NotBlank
        @Size(min = 1, max = 50)
        private String type;
        @Pattern(regexp = "available|pending|sold", message = "Invalid status")
        private String status;
    }

    @Data
    public static class StatusUpdateRequest {
        @NotBlank
        @Pattern(regexp = "available|pending|sold", message = "Invalid status")
        private String status;
    }

    @Data
    @AllArgsConstructor
    public static class Pet {
        private long technicalId; // corresponds to unique id from entityService
        private String name;
        private String type;
        private String status;
    }
}