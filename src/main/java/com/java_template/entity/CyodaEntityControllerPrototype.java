package com.java_template.entity;

import com.fasterxml.jackson.annotation.JsonIgnore;
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

import javax.annotation.PostConstruct;
import java.util.*;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;
import java.util.stream.Collectors;

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

    private String buildConditionFromSearchRequest(PetSearchRequest request) {
        // Build a simple condition string with AND logic, e.g. "category='xxx' AND status='yyy' AND name LIKE '%zzz%'"
        List<String> conditions = new ArrayList<>();
        if (request.getCategory() != null && !request.getCategory().isBlank()) {
            conditions.add("category='" + escapeSingleQuotes(request.getCategory()) + "'");
        }
        if (request.getStatus() != null && !request.getStatus().isBlank()) {
            conditions.add("status='" + escapeSingleQuotes(request.getStatus()) + "'");
        }
        if (request.getName() != null && !request.getName().isBlank()) {
            // Assuming the condition supports LIKE
            conditions.add("LOWER(name) LIKE '%" + escapeSingleQuotes(request.getName().toLowerCase()) + "%'");
        }
        return String.join(" AND ", conditions);
    }

    private String escapeSingleQuotes(String input) {
        return input.replace("'", "''");
    }

    @PostMapping("/add")
    public ResponseEntity<AddPetResponse> addPet(@RequestBody @Valid PetAddRequest request) throws Exception {
        logger.info("Adding new pet: {}", request);
        Pet pet = new Pet(null, request.getName(), request.getCategory(), request.getStatus(),
                request.getPhotoUrls(), request.getTags());

        CompletableFuture<UUID> idFuture = entityService.addItem(ENTITY_NAME, ENTITY_VERSION, pet);
        UUID technicalId = idFuture.get();

        return ResponseEntity.ok(new AddPetResponse(technicalId, "Pet added successfully"));
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

    @PostMapping("/update/{id}")
    public ResponseEntity<MessageResponse> updatePet(
            @PathVariable("id") UUID id,
            @RequestBody @Valid PetUpdateRequest request) throws Exception {
        logger.info("Updating pet id {} with data {}", id, request);
        CompletableFuture<ObjectNode> itemFuture = entityService.getItem(ENTITY_NAME, ENTITY_VERSION, id);
        ObjectNode node = itemFuture.get();
        if (node == null || node.isEmpty()) {
            throw new ResponseStatusException(org.springframework.http.HttpStatus.NOT_FOUND, "Pet not found");
        }
        Pet existingPet = objectMapper.treeToValue(node, Pet.class);
        existingPet.setTechnicalId(UUID.fromString(node.get("technicalId").asText()));

        if (request.getName() != null) existingPet.setName(request.getName());
        if (request.getCategory() != null) existingPet.setCategory(request.getCategory());
        if (request.getStatus() != null) existingPet.setStatus(request.getStatus());
        if (request.getPhotoUrls() != null) existingPet.setPhotoUrls(request.getPhotoUrls());
        if (request.getTags() != null) existingPet.setTags(request.getTags());

        CompletableFuture<UUID> updatedItemId = entityService.updateItem(ENTITY_NAME, ENTITY_VERSION, id, existingPet);
        updatedItemId.get();

        CompletableFuture.runAsync(() -> logger.info("Background update processing for pet id {}", id));
        return ResponseEntity.ok(new MessageResponse("Pet updated successfully"));
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

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    static class Pet {
        @JsonIgnore
        private UUID technicalId;
        private String name;
        private String category;
        private String status;
        private List<String> photoUrls;
        private List<String> tags;
    }

    @Data
    static class PetSearchRequest {
        @Size(max = 50)
        private String category;
        @Pattern(regexp = "available|pending|sold")
        private String status;
        @Size(max = 100)
        private String name;
    }

    @Data
    static class PetAddRequest {
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
    static class PetUpdateRequest {
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
    static class PetsResponse {
        private List<Pet> pets;
    }

    @Data
    @AllArgsConstructor
    static class AddPetResponse {
        private UUID id;
        private String message;
    }

    @Data
    @AllArgsConstructor
    static class MessageResponse {
        private String message;
    }
}