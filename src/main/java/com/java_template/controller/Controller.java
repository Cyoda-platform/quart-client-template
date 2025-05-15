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
import org.osgi.service.blueprint.annotation.Bean;
import org.osgi.service.blueprint.annotation.Reference;
import org.osgi.service.blueprint.annotation.Service;
import org.osgi.service.blueprint.annotation.Controller;
import org.osgi.service.blueprint.annotation.RequestMapping;
import org.osgi.service.blueprint.annotation.PathVariable;
import org.osgi.service.blueprint.annotation.PostMapping;
import org.osgi.service.blueprint.annotation.GetMapping;
import org.osgi.service.blueprint.annotation.RequestParam;
import org.osgi.service.blueprint.annotation.ResponseBody;
import org.osgi.service.blueprint.annotation.Validated;
import org.osgi.service.blueprint.annotation.RequestBody;
import org.osgi.service.blueprint.annotation.ResponseStatusException;
import org.osgi.service.blueprint.annotation.RequestMethod;
import org.osgi.service.blueprint.annotation.HttpStatus;

import java.util.*;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;

import static com.java_template.common.config.Config.*;

@Slf4j
@Validated
@Controller
@RequestMapping("/cyoda-pets")
@Service
@Bean(id = "cyodaEntityControllerPrototype")
public class CyodaEntityControllerPrototype {

    private final EntityService entityService;
    private final ObjectMapper objectMapper = new ObjectMapper();

    private static final String ENTITY_NAME = "pet";

    public CyodaEntityControllerPrototype(@Reference EntityService entityService) {
        this.entityService = entityService;
    }

    @PostMapping(value = "/add")
    @ResponseBody
    public AddPetResponse addPet(@RequestBody @Valid PetAddRequest request) throws ExecutionException, InterruptedException {
        log.info("Received add pet request: {}", request);

        ObjectNode petNode = objectMapper.valueToTree(request);

        CompletableFuture<UUID> idFuture = entityService.addItem(
                ENTITY_NAME,
                ENTITY_VERSION,
                petNode
        );
        UUID technicalId = idFuture.get();

        return new AddPetResponse(technicalId, "Pet added successfully");
    }

    @PostMapping(value = "/update/{id}")
    @ResponseBody
    public MessageResponse updatePet(
            @PathVariable("id") UUID id,
            @RequestBody @Valid PetUpdateRequest request) throws ExecutionException, InterruptedException {
        log.info("Received update pet request for id {}: {}", id, request);

        CompletableFuture<ObjectNode> itemFuture = entityService.getItem(ENTITY_NAME, ENTITY_VERSION, id);
        ObjectNode existingEntity = itemFuture.get();

        if (existingEntity == null || existingEntity.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Pet not found");
        }

        ObjectNode updateNode = objectMapper.valueToTree(request);
        updateNode.fieldNames().forEachRemaining(field -> {
            JsonNode value = updateNode.get(field);
            if (value != null && !value.isNull()) {
                existingEntity.set(field, value);
            }
        });

        CompletableFuture<UUID> updatedItemId = entityService.updateItem(ENTITY_NAME, ENTITY_VERSION, id, existingEntity);
        updatedItemId.get();

        return new MessageResponse("Pet updated successfully");
    }

    @PostMapping(value = "/search")
    @ResponseBody
    public PetsResponse searchPets(@RequestBody @Valid PetSearchRequest request) throws ExecutionException, InterruptedException {
        log.info("Received search request: {}", request);
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
        return new PetsResponse(matchedPets);
    }

    @GetMapping(value = "/{id}")
    @ResponseBody
    public Pet getPetById(@PathVariable("id") UUID id) throws ExecutionException, InterruptedException {
        log.info("Retrieving pet by id: {}", id);
        CompletableFuture<ObjectNode> itemFuture = entityService.getItem(ENTITY_NAME, ENTITY_VERSION, id);
        ObjectNode node = itemFuture.get();
        if (node == null || node.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Pet not found");
        }
        Pet pet = objectMapper.treeToValue(node, Pet.class);
        if (node.hasNonNull("technicalId")) {
            pet.setTechnicalId(UUID.fromString(node.get("technicalId").asText()));
        }
        return pet;
    }

    @GetMapping(value = "/list")
    @ResponseBody
    public PetsResponse listPets(
            @RequestParam(value = "category", required = false) @Size(max = 50) String category,
            @RequestParam(value = "status", required = false) @Pattern(regexp = "available|pending|sold") String status) throws ExecutionException, InterruptedException {
        log.info("Listing pets with filters: category={}, status={}", category, status);

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
        return new PetsResponse(filteredPets);
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