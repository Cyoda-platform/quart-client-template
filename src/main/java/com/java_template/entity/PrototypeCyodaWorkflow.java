package com.java_template.entity;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.java_template.common.service.EntityService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.util.*;
import java.util.concurrent.CompletableFuture;

import static com.java_template.common.config.Config.*;

@Slf4j
@Validated
@RestController
@RequestMapping("/cyoda-pets")
public class CyodaEntityControllerPrototype {

    private static final Logger logger = LoggerFactory.getLogger(CyodaEntityControllerPrototype.class);
    private final EntityService entityService;
    private final ObjectMapper objectMapper = new ObjectMapper();

    private static final String ENTITY_NAME = "pet";

    public CyodaEntityControllerPrototype(EntityService entityService) {
        this.entityService = entityService;
    }

    /**
     * Workflow function for processing Pet entity before persistence.
     * Receives the raw ObjectNode representing the entity.
     * Modify entity state by updating fields in the ObjectNode.
     * Can perform async tasks and add/get secondary entities of different entityModels.
     * Cannot add/update/delete entity of the same entityModel "pet" to avoid infinite recursion.
     */
    private CompletableFuture<ObjectNode> processPet(ObjectNode entity) {
        logger.info("Processing pet entity in workflow function");

        // Set default status if missing or empty
        JsonNode statusNode = entity.get("status");
        if (statusNode == null || statusNode.asText().isBlank()) {
            entity.put("status", "available");
        }

        // Example async fire-and-forget task: log pet name if present
        CompletableFuture.runAsync(() -> {
            String petName = entity.hasNonNull("name") ? entity.get("name").asText() : "unknown";
            logger.info("Async workflow task: Pet name is '{}'", petName);
        });

        // Example: Add or get secondary entities of different entityModels asynchronously if needed
        // Note: Do NOT add/update/delete entity of this entityModel "pet" here

        return CompletableFuture.completedFuture(entity);
    }

    @PostMapping("/add")
    public ResponseEntity<AddPetResponse> addPet(@RequestBody @Valid PetAddRequest request) throws Exception {
        logger.info("Received add pet request: {}", request);

        // Convert request DTO to ObjectNode for workflow compatibility
        ObjectNode petNode = objectMapper.valueToTree(request);

        // Call addItem with workflow function to process entity before persistence
        CompletableFuture<UUID> idFuture = entityService.addItem(
                ENTITY_NAME,
                ENTITY_VERSION,
                petNode,
                this::processPet
        );
        UUID technicalId = idFuture.get();

        return ResponseEntity.ok(new AddPetResponse(technicalId, "Pet added successfully"));
    }

    @PostMapping("/update/{id}")
    public ResponseEntity<MessageResponse> updatePet(
            @PathVariable("id") UUID id,
            @RequestBody @Valid PetUpdateRequest request) throws Exception {
        logger.info("Received update pet request for id {}: {}", id, request);

        // Retrieve existing entity as ObjectNode
        CompletableFuture<ObjectNode> itemFuture = entityService.getItem(ENTITY_NAME, ENTITY_VERSION, id);
        ObjectNode existingEntity = itemFuture.get();

        if (existingEntity == null || existingEntity.isEmpty()) {
            throw new ResponseStatusException(org.springframework.http.HttpStatus.NOT_FOUND, "Pet not found");
        }

        // Merge update request fields into existing entity ObjectNode
        ObjectNode updateNode = objectMapper.valueToTree(request);
        updateNode.fieldNames().forEachRemaining(field -> {
            JsonNode value = updateNode.get(field);
            if (value != null && !value.isNull()) {
                existingEntity.set(field, value);
            }
        });

        // Perform updateItem directly; no workflow support for update currently
        CompletableFuture<UUID> updatedItemId = entityService.updateItem(ENTITY_NAME, ENTITY_VERSION, id, existingEntity);
        updatedItemId.get();

        return ResponseEntity.ok(new MessageResponse("Pet updated successfully"));
    }

    @PostMapping("/search")
    public ResponseEntity<PetsResponse> searchPets(@RequestBody @Valid PetSearchRequest request) throws Exception {
        logger.info("Received search request: {}", request);
        String condition = buildConditionFromSearchRequest(request);
        CompletableFuture<ArrayNode> filteredItemsFuture = entityService.getItemsByCondition(
                ENTITY_NAME,
                ENTITY_VERSION,
                condition
        );
        ArrayNode filteredItems = filteredItemsFuture.get();

        List<Pet> matchedPets = new ArrayList<>();
        for (int i = 0; i < filteredItems.size(); i++) {
            ObjectNode node = (ObjectNode) filteredItems.get(i);
            Pet pet = objectMapper.treeToValue(node, Pet.class);
            if (node.hasNonNull("technicalId")) {
                pet.setTechnicalId(UUID.fromString(node.get("technicalId").asText()));
            }
            matchedPets.add(pet);
        }
        return ResponseEntity.ok(new PetsResponse(matchedPets));
    }

    @GetMapping("/{id}")
    public ResponseEntity<Pet> getPetById(@PathVariable("id") UUID id) throws Exception {
        logger.info("Retrieving pet by id: {}", id);
        CompletableFuture<ObjectNode> itemFuture = entityService.getItem(ENTITY_NAME, ENTITY_VERSION, id);
        ObjectNode node = itemFuture.get();
        if (node == null || node.isEmpty()) {
            throw new ResponseStatusException(org.springframework.http.HttpStatus.NOT_FOUND, "Pet not found");
        }
        Pet pet = objectMapper.treeToValue(node, Pet.class);
        if (node.hasNonNull("technicalId")) {
            pet.setTechnicalId(UUID.fromString(node.get("technicalId").asText()));
        }
        return ResponseEntity.ok(pet);
    }

    @GetMapping("/list")
    public ResponseEntity<PetsResponse> listPets(
            @RequestParam(required = false) @Size(max = 50) String category,
            @RequestParam(required = false) @Pattern(regexp = "available|pending|sold") String status) throws Exception {
        logger.info("Listing pets with filters: category={}, status={}", category, status);

        String condition = buildConditionFromParams(category, status);
        CompletableFuture<ArrayNode> filteredItemsFuture;

        if (condition.isBlank()) {
            filteredItemsFuture = entityService.getItems(ENTITY_NAME, ENTITY_VERSION);
        } else {
            filteredItemsFuture = entityService.getItemsByCondition(ENTITY_NAME, ENTITY_VERSION, condition);
        }

        ArrayNode items = filteredItemsFuture.get();
        List<Pet> filteredPets = new ArrayList<>();
        for (int i = 0; i < items.size(); i++) {
            ObjectNode node = (ObjectNode) items.get(i);
            Pet pet = objectMapper.treeToValue(node, Pet.class);
            if (node.hasNonNull("technicalId")) {
                pet.setTechnicalId(UUID.fromString(node.get("technicalId").asText()));
            }
            filteredPets.add(pet);
        }
        return ResponseEntity.ok(new PetsResponse(filteredPets));
    }

    private String buildConditionFromSearchRequest(PetSearchRequest request) {
        List<String> conditions = new ArrayList<>();
        if (request.getCategory() != null && !request.getCategory().isBlank()) {
            conditions.add("category='" + escapeSingleQuotes(request.getCategory()) + "'");
        }
        if (request.getStatus() != null && !request.getStatus().isBlank()) {
            conditions.add("status='" + escapeSingleQuotes(request.getStatus()) + "'");
        }
        if (request.getName() != null && !request.getName().isBlank()) {
            conditions.add("LOWER(name) LIKE '%" + escapeSingleQuotes(request.getName().toLowerCase()) + "%'");
        }
        return String.join(" AND ", conditions);
    }

    private String buildConditionFromParams(String category, String status) {
        List<String> conditions = new ArrayList<>();
        if (category != null && !category.isBlank()) {
            conditions.add("category='" + escapeSingleQuotes(category) + "'");
        }
        if (status != null && !status.isBlank()) {
            conditions.add("status='" + escapeSingleQuotes(status) + "'");
        }
        return String.join(" AND ", conditions);
    }

    private String escapeSingleQuotes(String input) {
        return input.replace("'", "''");
    }

    // DTOs and entity POJO

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Pet {
        @com.fasterxml.jackson.annotation.JsonIgnore
        private UUID technicalId;
        private String name;
        private String category;
        private String status;
        private List<String> photoUrls;
        private List<String> tags;
    }

    @Data
    public static class PetSearchRequest {
        @Size(max = 50)
        private String category;
        @Pattern(regexp = "available|pending|sold")
        private String status;
        @Size(max = 100)
        private String name;
    }

    @Data
    public static class PetAddRequest {
        @NotBlank
        @Size(max = 100)
        private String name;
        @Size(max = 50)
        private String category;
        @Pattern(regexp = "available|pending|sold")
        private String status;
        @Size(max = 10)
        private List<@NotBlank String> photoUrls;
        @Size(max = 10)
        private List<@NotBlank String> tags;
    }

    @Data
    public static class PetUpdateRequest {
        @Size(max = 100)
        private String name;
        @Size(max = 50)
        private String category;
        @Pattern(regexp = "available|pending|sold")
        private String status;
        @Size(max = 10)
        private List<@NotBlank String> photoUrls;
        @Size(max = 10)
        private List<@NotBlank String> tags;
    }

    @Data
    @AllArgsConstructor
    public static class PetsResponse {
        private List<Pet> pets;
    }

    @Data
    @AllArgsConstructor
    public static class AddPetResponse {
        private UUID id;
        private String message;
    }

    @Data
    @AllArgsConstructor
    public static class MessageResponse {
        private String message;
    }
}