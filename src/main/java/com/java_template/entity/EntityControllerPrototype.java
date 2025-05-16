```java
package com.java_template.entity;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.scheduling.annotation.Async;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@RestController
@RequestMapping("/pets")
public class EntityControllerPrototype {

    private static final Logger logger = LoggerFactory.getLogger(EntityControllerPrototype.class);
    private static final String PETSTORE_API_BASE = "https://petstore.swagger.io/v2";

    private final RestTemplate restTemplate = new RestTemplate();
    private final ObjectMapper objectMapper = new ObjectMapper();

    // In-memory store for pets keyed by id
    private final Map<Long, Pet> petStore = new ConcurrentHashMap<>();

    @PostMapping
    public ResponseEntity<PetResponse> addOrUpdatePet(@RequestBody PetRequest request) {
        logger.info("Received POST /pets with action: {}", request.getAction());

        try {
            switch (request.getAction()) {
                case "fetch":
                    // Fetch pet data from external Petstore API by id
                    if (request.getPetData() == null || request.getPetData().getId() == null) {
                        throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Pet id required for fetch action");
                    }
                    Pet fetchedPet = fetchPetFromExternalApi(request.getPetData().getId());
                    petStore.put(fetchedPet.getId(), fetchedPet);
                    return ResponseEntity.ok(new PetResponse(true, fetchedPet));

                case "add":
                    // Add pet locally with new id if not provided
                    Pet petToAdd = request.getPetData();
                    if (petToAdd == null) {
                        throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Pet data required for add");
                    }
                    if (petToAdd.getId() == null) {
                        petToAdd.setId(generateId());
                    }
                    petStore.put(petToAdd.getId(), petToAdd);
                    return ResponseEntity.ok(new PetResponse(true, petToAdd));

                case "update":
                    // Update existing pet locally
                    Pet petToUpdate = request.getPetData();
                    if (petToUpdate == null || petToUpdate.getId() == null) {
                        throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Pet id and data required for update");
                    }
                    if (!petStore.containsKey(petToUpdate.getId())) {
                        throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Pet not found");
                    }
                    petStore.put(petToUpdate.getId(), petToUpdate);
                    return ResponseEntity.ok(new PetResponse(true, petToUpdate));

                default:
                    throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Unknown action: " + request.getAction());
            }
        } catch (ResponseStatusException ex) {
            logger.error("Error in addOrUpdatePet: {}", ex.getReason());
            throw ex;
        } catch (Exception ex) {
            logger.error("Unexpected error in addOrUpdatePet", ex);
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "Internal server error");
        }
    }

    @PostMapping("/search")
    public ResponseEntity<SearchResponse> searchPets(@RequestBody SearchRequest request) {
        logger.info("Received POST /pets/search with filters: {}", request.getFilters());

        try {
            // TODO: In real app, fetch filtered data from external API or DB.
            // Here, simulate fetching from external Petstore API /pet/findByStatus or /pet/findByTags

            List<Pet> results = new ArrayList<>();

            // If status filter is present, call external API /pet/findByStatus
            if (request.getFilters() != null && request.getFilters().getStatus() != null) {
                String status = request.getFilters().getStatus();
                String url = PETSTORE_API_BASE + "/pet/findByStatus?status=" + status;
                String jsonResponse = restTemplate.getForObject(url, String.class);
                JsonNode root = objectMapper.readTree(jsonResponse);
                if (root.isArray()) {
                    for (JsonNode node : root) {
                        Pet p = jsonNodeToPet(node);
                        if (matchesFilters(p, request.getFilters())) {
                            results.add(p);
                            petStore.put(p.getId(), p); // Cache locally
                        }
                    }
                }
            } else {
                // For simplicity, search local petStore applying filters
                petStore.values().stream()
                        .filter(p -> matchesFilters(p, request.getFilters()))
                        .forEach(results::add);
            }

            return ResponseEntity.ok(new SearchResponse(results));
        } catch (Exception ex) {
            logger.error("Error in searchPets", ex);
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "Internal server error");
        }
    }

    @GetMapping("/{id}")
    public ResponseEntity<Pet> getPetById(@PathVariable Long id) {
        logger.info("Received GET /pets/{}", id);
        Pet pet = petStore.get(id);
        if (pet == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Pet not found");
        }
        return ResponseEntity.ok(pet);
    }

    // Helper: fetch pet from external API by id
    private Pet fetchPetFromExternalApi(Long id) throws Exception {
        String url = PETSTORE_API_BASE + "/pet/" + id;
        logger.info("Fetching pet from external API: {}", url);
        String jsonResponse = restTemplate.getForObject(url, String.class);
        JsonNode root = objectMapper.readTree(jsonResponse);
        return jsonNodeToPet(root);
    }

    private Pet jsonNodeToPet(JsonNode node) {
        Pet pet = new Pet();
        pet.setId(node.hasNonNull("id") ? node.get("id").asLong() : null);
        pet.setName(node.hasNonNull("name") ? node.get("name").asText() : null);
        pet.setStatus(node.hasNonNull("status") ? node.get("status").asText() : null);

        if (node.has("category") && node.get("category").hasNonNull("name")) {
            pet.setCategory(node.get("category").get("name").asText());
        } else {
            pet.setCategory(null);
        }

        if (node.has("tags") && node.get("tags").isArray()) {
            List<String> tags = new ArrayList<>();
            for (JsonNode tagNode : node.get("tags")) {
                if (tagNode.hasNonNull("name")) {
                    tags.add(tagNode.get("name").asText());
                }
            }
            pet.setTags(tags);
        } else {
            pet.setTags(Collections.emptyList());
        }
        return pet;
    }

    private boolean matchesFilters(Pet pet, Filters filters) {
        if (filters == null) return true;
        if (filters.getCategory() != null && (pet.getCategory() == null || !pet.getCategory().equalsIgnoreCase(filters.getCategory())))
            return false;
        if (filters.getStatus() != null && (pet.getStatus() == null || !pet.getStatus().equalsIgnoreCase(filters.getStatus())))
            return false;
        if (filters.getName() != null && (pet.getName() == null || !pet.getName().toLowerCase().contains(filters.getName().toLowerCase())))
            return false;
        return true;
    }

    private Long generateId() {
        return new Random().nextLong() & Long.MAX_VALUE; // positive random id
    }

    // --- Data classes ---

    @Data
    public static class PetRequest {
        private String action; // "fetch", "add", "update"
        private Pet petData;
    }

    @Data
    @AllArgsConstructor
    public static class PetResponse {
        private boolean success;
        private Pet pet;
    }

    @Data
    public static class SearchRequest {
        private Filters filters;
    }

    @Data
    public static class SearchResponse {
        private List<Pet> pets;

        public SearchResponse(List<Pet> pets) {
            this.pets = pets != null ? pets : Collections.emptyList();
        }
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Pet {
        private Long id;
        private String name;
        private String category;
        private String status; // available | pending | sold
        private List<String> tags = new ArrayList<>();
    }

    @Data
    public static class Filters {
        private String category;
        private String status;
        private String name;
    }

    // --- Basic exception handler ---
    @ExceptionHandler(ResponseStatusException.class)
    public ResponseEntity<Map<String, String>> handleResponseStatusException(ResponseStatusException ex) {
        logger.error("Handling ResponseStatusException: {}", ex.getReason());
        Map<String, String> error = new HashMap<>();
        error.put("error", ex.getReason());
        return ResponseEntity.status(ex.getStatusCode()).body(error);
    }

}
```
