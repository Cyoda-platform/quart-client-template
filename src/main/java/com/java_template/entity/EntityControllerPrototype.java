```java
package com.java_template.entity;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.server.ResponseStatusException;

import javax.annotation.PostConstruct;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CompletableFuture;

@Slf4j
@RestController
@RequestMapping("/pets")
public class EntityControllerPrototype {

    private final RestTemplate restTemplate = new RestTemplate();
    private final ObjectMapper objectMapper = new ObjectMapper();

    // In-memory pet storage to simulate persistence
    private final Map<Long, Pet> petStore = new ConcurrentHashMap<>();
    private long idCounter = 1L;

    // Endpoint of external Petstore API
    private static final String PETSTORE_API_BASE = "https://petstore.swagger.io/v2";

    @PostConstruct
    public void init() {
        log.info("EntityControllerPrototype initialized");
    }

    /**
     * POST /pets/search
     * Search pets by filters using external Petstore API
     */
    @PostMapping("/search")
    public ResponseEntity<PetsResponse> searchPets(@RequestBody PetSearchRequest request) {
        log.info("Received search request: {}", request);

        try {
            // Build query params for Petstore API
            StringBuilder urlBuilder = new StringBuilder(PETSTORE_API_BASE + "/pet/findByStatus?status=");
            if (request.getStatus() != null && !request.getStatus().isEmpty()) {
                urlBuilder.append(request.getStatus());
            } else {
                // Petstore requires status param, default to available
                urlBuilder.append("available");
            }

            String url = urlBuilder.toString();
            log.info("Calling Petstore API: {}", url);

            String responseStr = restTemplate.getForObject(url, String.class);
            JsonNode root = objectMapper.readTree(responseStr);

            List<Pet> matchedPets = new ArrayList<>();

            if (root.isArray()) {
                for (JsonNode petNode : root) {
                    Pet pet = fromPetstoreJson(petNode);
                    if (matchesFilters(pet, request)) {
                        matchedPets.add(pet);
                    }
                }
            } else {
                log.warn("Unexpected JSON structure from Petstore API");
            }

            PetsResponse response = new PetsResponse(matchedPets);
            return ResponseEntity.ok(response);

        } catch (Exception ex) {
            log.error("Error searching pets", ex);
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "Failed to search pets");
        }
    }

    /**
     * POST /pets/add
     * Add a new pet locally (business logic can be extended)
     */
    @PostMapping("/add")
    public ResponseEntity<AddPetResponse> addPet(@RequestBody PetAddRequest request) {
        log.info("Adding new pet: {}", request);

        if (request.getName() == null || request.getName().isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Pet name is required");
        }

        long newId = generateId();
        Pet pet = new Pet(
                newId,
                request.getName(),
                request.getCategory(),
                request.getStatus(),
                request.getPhotoUrls() != null ? request.getPhotoUrls() : Collections.emptyList(),
                request.getTags() != null ? request.getTags() : Collections.emptyList()
        );

        petStore.put(newId, pet);

        // TODO: Fire-and-forget event workflow for pet lifecycle (e.g., notify external systems)
        CompletableFuture.runAsync(() -> {
            log.info("Background processing for pet id {}", newId);
            // Placeholder for async workflow logic
        });

        return ResponseEntity.ok(new AddPetResponse(newId, "Pet added successfully"));
    }

    /**
     * GET /pets/{id}
     * Retrieve pet details by id from local store
     */
    @GetMapping("/{id}")
    public ResponseEntity<Pet> getPetById(@PathVariable("id") Long id) {
        log.info("Retrieving pet by id: {}", id);
        Pet pet = petStore.get(id);
        if (pet == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Pet not found");
        }
        return ResponseEntity.ok(pet);
    }

    /**
     * POST /pets/update/{id}
     * Update pet data partially
     */
    @PostMapping("/update/{id}")
    public ResponseEntity<MessageResponse> updatePet(
            @PathVariable("id") Long id,
            @RequestBody PetUpdateRequest request) {
        log.info("Updating pet id {} with data {}", id, request);

        Pet existingPet = petStore.get(id);
        if (existingPet == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Pet not found");
        }

        if (request.getName() != null)
            existingPet.setName(request.getName());
        if (request.getCategory() != null)
            existingPet.setCategory(request.getCategory());
        if (request.getStatus() != null)
            existingPet.setStatus(request.getStatus());
        if (request.getPhotoUrls() != null)
            existingPet.setPhotoUrls(request.getPhotoUrls());
        if (request.getTags() != null)
            existingPet.setTags(request.getTags());

        petStore.put(id, existingPet);

        // TODO: Fire-and-forget event workflow for pet update lifecycle
        CompletableFuture.runAsync(() -> {
            log.info("Background update processing for pet id {}", id);
            // Placeholder for async workflow logic
        });

        return ResponseEntity.ok(new MessageResponse("Pet updated successfully"));
    }

    /**
     * GET /pets/list
     * List all pets or filtered by optional query params
     */
    @GetMapping("/list")
    public ResponseEntity<PetsResponse> listPets(
            @RequestParam(name = "category", required = false) String category,
            @RequestParam(name = "status", required = false) String status) {
        log.info("Listing pets with filters: category={}, status={}", category, status);

        List<Pet> filteredPets = new ArrayList<>();
        for (Pet pet : petStore.values()) {
            boolean matches = true;
            if (category != null && !category.isBlank()) {
                matches &= category.equalsIgnoreCase(pet.getCategory());
            }
            if (status != null && !status.isBlank()) {
                matches &= status.equalsIgnoreCase(pet.getStatus());
            }
            if (matches) {
                filteredPets.add(pet);
            }
        }

        return ResponseEntity.ok(new PetsResponse(filteredPets));
    }

    // --- Helper methods and classes ---

    private boolean matchesFilters(Pet pet, PetSearchRequest filters) {
        if (filters.getCategory() != null && !filters.getCategory().isBlank()) {
            if (!filters.getCategory().equalsIgnoreCase(pet.getCategory())) return false;
        }
        if (filters.getStatus() != null && !filters.getStatus().isBlank()) {
            if (!filters.getStatus().equalsIgnoreCase(pet.getStatus())) return false;
        }
        if (filters.getName() != null && !filters.getName().isBlank()) {
            if (pet.getName() == null || !pet.getName().toLowerCase().contains(filters.getName().toLowerCase())) {
                return false;
            }
        }
        return true;
    }

    private Pet fromPetstoreJson(JsonNode petNode) {
        Long id = petNode.has("id") && petNode.get("id").canConvertToLong() ? petNode.get("id").longValue() : null;
        String name = petNode.has("name") ? petNode.get("name").asText() : null;
        String status = petNode.has("status") ? petNode.get("status").asText() : null;

        String category = null;
        if (petNode.has("category") && petNode.get("category").has("name")) {
            category = petNode.get("category").get("name").asText();
        }

        List<String> photoUrls = new ArrayList<>();
        if (petNode.has("photoUrls") && petNode.get("photoUrls").isArray()) {
            for (JsonNode urlNode : petNode.get("photoUrls")) {
                photoUrls.add(urlNode.asText());
            }
        }

        List<String> tags = new ArrayList<>();
        if (petNode.has("tags") && petNode.get("tags").isArray()) {
            for (JsonNode tagNode : petNode.get("tags")) {
                if (tagNode.has("name")) {
                    tags.add(tagNode.get("name").asText());
                }
            }
        }

        return new Pet(id, name, category, status, photoUrls, tags);
    }

    private synchronized long generateId() {
        return idCounter++;
    }

    // --- DTO and Model classes ---

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    static class Pet {
        private Long id;
        private String name;
        private String category;
        private String status;
        private List<String> photoUrls = new ArrayList<>();
        private List<String> tags = new ArrayList<>();
    }

    @Data
    static class PetSearchRequest {
        private String category;
        private String status;
        private String name;
    }

    @Data
    static class PetAddRequest {
        private String name;
        private String category;
        private String status;
        private List<String> photoUrls;
        private List<String> tags;
    }

    @Data
    static class PetUpdateRequest {
        private String name;
        private String category;
        private String status;
        private List<String> photoUrls;
        private List<String> tags;
    }

    @Data
    @AllArgsConstructor
    static class PetsResponse {
        private List<Pet> pets;
    }

    @Data
    @AllArgsConstructor
    static class AddPetResponse {
        private Long id;
        private String message;
    }

    @Data
    @AllArgsConstructor
    static class MessageResponse {
        private String message;
    }

    // Minimal exception handler to convert exceptions to HTTP responses
    @ExceptionHandler(ResponseStatusException.class)
    public ResponseEntity<Map<String, Object>> handleResponseStatusException(ResponseStatusException ex) {
        Map<String, Object> error = new HashMap<>();
        error.put("status", ex.getStatusCode().value());
        error.put("error", ex.getStatusCode().getReasonPhrase());
        error.put("message", ex.getReason());
        return new ResponseEntity<>(error, ex.getStatusCode());
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<Map<String, Object>> handleGenericException(Exception ex) {
        log.error("Unhandled exception", ex);
        Map<String, Object> error = new HashMap<>();
        error.put("status", HttpStatus.INTERNAL_SERVER_ERROR.value());
        error.put("error", HttpStatus.INTERNAL_SERVER_ERROR.getReasonPhrase());
        error.put("message", "Internal server error");
        return new ResponseEntity<>(error, HttpStatus.INTERNAL_SERVER_ERROR);
    }
}
```
