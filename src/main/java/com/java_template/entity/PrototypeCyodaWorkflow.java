package com.java_template.entity;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.java_template.common.service.EntityService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.server.ResponseStatusException;

import java.util.*;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;

import static com.java_template.common.config.Config.*;

@RestController
@Validated
@RequestMapping("/cyoda-pets")
public class CyodaEntityControllerPrototype {

    private static final Logger logger = LoggerFactory.getLogger(CyodaEntityControllerPrototype.class);
    private static final String PETSTORE_API_BASE = "https://petstore.swagger.io/v2";

    private final EntityService entityService;
    private final RestTemplate restTemplate = new RestTemplate();
    private final ObjectMapper mapper = new ObjectMapper();

    public CyodaEntityControllerPrototype(EntityService entityService) {
        this.entityService = entityService;
    }

    /**
     * Workflow function processpet.
     * Runs asynchronously before persisting the 'pet' entity.
     * Receives ObjectNode representing the pet entity.
     * Can modify entity state directly.
     * Can get/add other entities of different models asynchronously.
     * Cannot add/update/delete 'pet' entity itself to avoid recursion.
     */
    private CompletableFuture<ObjectNode> processpet(ObjectNode petNode) {
        // Defensive copy if needed - here just use the given node directly
        // Generate id if missing or zero
        if (!petNode.hasNonNull("id") || petNode.get("id").asLong(0L) == 0L) {
            long generatedId = new Random().nextLong() & Long.MAX_VALUE;
            petNode.put("id", generatedId);
            logger.debug("processpet: Generated new id {}", generatedId);
        }

        // If pet has id but missing name, attempt to fetch from external API and enrich entity
        if (petNode.hasNonNull("id") && (!petNode.hasNonNull("name") || petNode.get("name").asText().isEmpty())) {
            long petId = petNode.get("id").asLong();
            logger.debug("processpet: Fetching external data for pet id {}", petId);

            return CompletableFuture.supplyAsync(() -> {
                try {
                    String url = PETSTORE_API_BASE + "/pet/" + petId;
                    String responseBody = restTemplate.getForObject(url, String.class);
                    if (responseBody == null) {
                        logger.warn("processpet: Empty response from external API for id {}", petId);
                        return petNode;
                    }
                    JsonNode extPetNode = mapper.readTree(responseBody);
                    // Update petNode fields if missing or overwrite as needed
                    if (extPetNode.hasNonNull("name")) petNode.put("name", extPetNode.get("name").asText());
                    if (extPetNode.hasNonNull("status")) petNode.put("status", extPetNode.get("status").asText());

                    if (extPetNode.hasNonNull("category") && extPetNode.get("category").hasNonNull("name")) {
                        petNode.put("category", extPetNode.get("category").get("name").asText());
                    }

                    // Add a supplementary entity of different model, e.g., "petAudit"
                    ObjectNode auditNode = mapper.createObjectNode();
                    auditNode.put("petId", petId);
                    auditNode.put("action", "fetched");
                    auditNode.put("timestamp", System.currentTimeMillis());

                    // Add audit entity asynchronously - different model, allowed
                    entityService.addItem("petAudit", ENTITY_VERSION, auditNode, obj -> CompletableFuture.completedFuture(obj));

                    return petNode;
                } catch (Exception e) {
                    logger.error("processpet: Error fetching external pet data", e);
                    // On failure, just return original node (no enrichment)
                    return petNode;
                }
            });
        }

        // No async fetch needed, return completed future quickly
        return CompletableFuture.completedFuture(petNode);
    }

    @PostMapping
    public ResponseEntity<PetResponse> addOrUpdatePet(@RequestBody @Valid PetRequest request) throws ExecutionException, InterruptedException {
        logger.info("POST /cyoda-pets action={}", request.getAction());

        ObjectNode petNode = mapper.createObjectNode();

        if ("fetch".equals(request.getAction())) {
            if (request.getId() == null) {
                throw new ResponseStatusException(ResponseStatusException.Status.REQUESTED_RANGE_NOT_SATISFIABLE, "id required");
            }
            petNode.put("id", request.getId());
            // enrichment and external fetch will be done in workflow
        } else if ("add".equals(request.getAction()) || "update".equals(request.getAction())) {
            if ("update".equals(request.getAction()) && request.getId() == null) {
                throw new ResponseStatusException(ResponseStatusException.Status.NOT_FOUND, "id not found");
            }
            if (request.getId() != null) {
                petNode.put("id", request.getId());
            }
            if (request.getName() != null) petNode.put("name", request.getName());
            if (request.getCategory() != null) petNode.put("category", request.getCategory());
            if (request.getStatus() != null) petNode.put("status", request.getStatus());
        } else {
            throw new ResponseStatusException(ResponseStatusException.Status.BAD_REQUEST, "unknown action");
        }

        CompletableFuture<UUID> futureId = entityService.addItem(
                "pet",
                ENTITY_VERSION,
                petNode,
                this::processpet
        );
        UUID technicalId = futureId.get();

        petNode.put("technicalId", technicalId.toString());

        Pet petResponse = mapper.convertValue(petNode, Pet.class);

        return ResponseEntity.ok(new PetResponse(true, petResponse));
    }

    @PostMapping("/search")
    public ResponseEntity<SearchResponse> searchPets(@RequestBody @Valid SearchRequest req) throws ExecutionException, InterruptedException {
        logger.info("POST /cyoda-pets/search filters={}", req);

        List<Pet> list = new ArrayList<>();

        CompletableFuture<com.fasterxml.jackson.databind.node.ArrayNode> itemsFuture = entityService.getItems("pet", ENTITY_VERSION);
        com.fasterxml.jackson.databind.node.ArrayNode items = itemsFuture.get();

        for (JsonNode node : items) {
            boolean matches = true;

            if (req.getStatus() != null) {
                String status = node.hasNonNull("status") ? node.get("status").asText() : "";
                if (!req.getStatus().equalsIgnoreCase(status)) matches = false;
            }
            if (req.getCategory() != null) {
                String category = node.hasNonNull("category") ? node.get("category").asText() : "";
                if (!req.getCategory().equalsIgnoreCase(category)) matches = false;
            }
            if (req.getName() != null) {
                String name = node.hasNonNull("name") ? node.get("name").asText().toLowerCase() : "";
                if (!name.contains(req.getName().toLowerCase())) matches = false;
            }
            if (matches) {
                Pet p = mapper.convertValue(node, Pet.class);
                list.add(p);
            }
        }

        return ResponseEntity.ok(new SearchResponse(list));
    }

    @GetMapping("/{id}")
    public ResponseEntity<Pet> getPet(@PathVariable Long id) throws ExecutionException, InterruptedException {
        logger.info("GET /cyoda-pets/{}", id);

        CompletableFuture<com.fasterxml.jackson.databind.node.ArrayNode> itemsFuture = entityService.getItemsByCondition("pet", ENTITY_VERSION, "id=" + id);
        com.fasterxml.jackson.databind.node.ArrayNode arr = itemsFuture.get();

        if (arr.size() == 0) {
            throw new ResponseStatusException(ResponseStatusException.Status.NOT_FOUND, "not found");
        }

        Pet p = mapper.convertValue(arr.get(0), Pet.class);
        return ResponseEntity.ok(p);
    }

    @Data
    public static class PetRequest {
        @NotNull
        @Pattern(regexp = "fetch|add|update")
        private String action;
        private Long id;
        private String name;
        private String category;
        private String status;
    }

    @Data
    @AllArgsConstructor
    public static class PetResponse {
        private boolean success;
        private Pet pet;
    }

    @Data
    public static class SearchRequest {
        private String category;
        private String status;
        private String name;
    }

    @Data
    @AllArgsConstructor
    public static class SearchResponse {
        private List<Pet> pets;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Pet {
        private Long id;
        private String name;
        private String category;
        private String status;
        private String technicalId;
    }

}