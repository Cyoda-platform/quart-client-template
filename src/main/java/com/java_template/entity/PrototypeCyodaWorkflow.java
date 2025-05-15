Certainly! To make the controller leaner and move all asynchronous and entity-preparation logic into the workflow function `processPet`, we can:

- Move any async "fire-and-forget" tasks and entity modification logic from controller methods into the `processPet` method.
- Use `ObjectNode` as the function argument and modify it directly as required (instead of using `Pet` POJO), since the workflow function works with raw JSON entity data.
- Keep the controller endpoints focused purely on HTTP handling and validation, delegating business logic and async workflows to the workflow function.

---

### Updated code with all async logic moved into `processPet` workflow function:

```java
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
import java.util.function.Function;

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
     * This function receives the raw ObjectNode representing the entity.
     * Modify the entity state directly by updating fields in the ObjectNode.
     *
     * You can get/add secondary entities of other entityModels here asynchronously.
     * Do NOT add/update/delete entity of the same entityModel "pet" inside this function.
     */
    private CompletableFuture<ObjectNode> processPet(ObjectNode entity) {
        logger.info("Processing pet entity in workflow function");

        // Set default status if missing or empty
        JsonNode statusNode = entity.get("status");
        if (statusNode == null || statusNode.asText().isBlank()) {
            entity.put("status", "available");
        }

        // Example: Fire-and-forget async logging or other async task
        CompletableFuture.runAsync(() -> logger.info("Async task inside workflow for pet: {}", entity));

        // Example: You can add/get secondary entities of different entityModel here if needed.
        // For example:
        // CompletableFuture<UUID> relatedEntityId = entityService.addItem("relatedEntityModel", ENTITY_VERSION, relatedEntityData, null);
        // You can chain or combine these futures if needed.

        // Return completed future with the modified entity
        return CompletableFuture.completedFuture(entity);
    }

    @PostMapping("/add")
    public ResponseEntity<AddPetResponse> addPet(@RequestBody @Valid PetAddRequest request) throws Exception {
        logger.info("Received add pet request: {}", request);

        // Convert request DTO to ObjectNode instead of Pet POJO to work directly with raw JSON entity
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

        // For updateItem, workflow function is NOT required (as per current requirements)
        CompletableFuture<UUID> updatedItemId = entityService.updateItem(ENTITY_NAME, ENTITY_VERSION, id, existingEntity);
        updatedItemId.get();

        // Previously we had a fire-and-forget async log here, move into workflow if needed
        // Since updateItem does not accept workflow, optionally create a separate async method here or skip

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
            pet.setTechnicalId(UUID.fromString(node.get("technicalId").asText()));
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
        pet.setTechnicalId(UUID.fromString(node.get("technicalId").asText()));
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
            pet.setTechnicalId(UUID.fromString(node.get("technicalId").asText()));
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
        @JsonIgnore
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
```

---

### Summary of improvements:
- `processPet(ObjectNode entity)` is now the single place where:
  - Entity defaulting (like status) is handled.
  - Async "fire-and-forget" tasks related to the entity can be executed.
  - Supplementary entities can be added or fetched asynchronously.
- Controller methods just convert request DTOs to `ObjectNode` and delegate persistence to `entityService.addItem` with the workflow function.
- Update method merges update fields into existing entity JSON and saves directly.
- This decouples business logic and async workflows from endpoint handlers, improving maintainability and robustness.

Let me know if you want me to help move update-related async tasks into a workflow function too, if that becomes supported in the future!