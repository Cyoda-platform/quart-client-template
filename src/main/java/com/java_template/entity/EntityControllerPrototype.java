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
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.server.ResponseStatusException;

import javax.annotation.PostConstruct;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@RestController
@RequestMapping("/pets")
public class EntityControllerPrototype {

    private static final Logger logger = LoggerFactory.getLogger(EntityControllerPrototype.class);

    private final RestTemplate restTemplate = new RestTemplate();
    private final ObjectMapper objectMapper = new ObjectMapper();

    // In-memory pet storage: id -> Pet
    private final Map<Long, Pet> pets = new ConcurrentHashMap<>();
    private long petIdSequence = 1;

    // Sample list of fun pet facts
    private final List<String> petFacts = Arrays.asList(
            "Cats sleep for 70% of their lives.",
            "Dogs have three eyelids.",
            "A group of cats is called a clowder.",
            "Rabbits can see behind them without turning their heads."
    );

    private static final String PETSTORE_API_BASE = "https://petstore.swagger.io/v2";

    @PostConstruct
    public void init() {
        // Optionally preload some pets or leave empty for prototype
        logger.info("EntityControllerPrototype initialized");
    }

    /**
     * POST /pets/fetch
     * Fetch pets data from external Petstore API and update local storage.
     */
    @PostMapping(value = "/fetch", consumes = MediaType.APPLICATION_JSON_VALUE, produces = MediaType.APPLICATION_JSON_VALUE)
    public Map<String, Object> fetchPets(@RequestBody(required = false) FetchFilter filter) {
        logger.info("Fetching pets from external Petstore API with filter: {}", filter);

        String statusFilter = (filter != null && filter.status != null) ? filter.status : "";

        String url = PETSTORE_API_BASE + "/pet/findByStatus?status=" + statusFilter;

        try {
            String jsonResponse = restTemplate.getForObject(url, String.class);
            JsonNode root = objectMapper.readTree(jsonResponse);

            if (!root.isArray()) {
                throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "Unexpected response format from Petstore API");
            }

            int updatedCount = 0;
            for (JsonNode petNode : root) {
                // Extract minimal pet info: id, name, status, category/type
                long id = petNode.path("id").asLong(-1);
                if (id == -1) continue; // skip invalid

                String name = petNode.path("name").asText("Unnamed");
                String status = petNode.path("status").asText("unknown");
                String type = petNode.path("category").path("name").asText("Unknown");

                Pet pet = new Pet(id, name, type, status);
                pets.put(id, pet);
                updatedCount++;
            }

            logger.info("Fetched and updated {} pets", updatedCount);

            Map<String, Object> response = new HashMap<>();
            response.put("message", "Pets data fetched and updated successfully");
            response.put("count", updatedCount);
            return response;

        } catch (Exception e) {
            logger.error("Error fetching pets from external API", e);
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "Failed to fetch pets from external API");
        }
    }

    /**
     * GET /pets
     * Retrieve list of pets optionally filtered by status.
     */
    @GetMapping(produces = MediaType.APPLICATION_JSON_VALUE)
    public List<Pet> listPets(@RequestParam(required = false) String status) {
        logger.info("Listing pets with status filter: {}", status);
        if (status == null || status.isEmpty()) {
            return new ArrayList<>(pets.values());
        }
        List<Pet> filtered = new ArrayList<>();
        for (Pet pet : pets.values()) {
            if (status.equalsIgnoreCase(pet.getStatus())) {
                filtered.add(pet);
            }
        }
        return filtered;
    }

    /**
     * POST /pets
     * Add a new pet locally.
     */
    @PostMapping(consumes = MediaType.APPLICATION_JSON_VALUE, produces = MediaType.APPLICATION_JSON_VALUE)
    public Map<String, Object> addPet(@RequestBody PetCreateRequest request) {
        logger.info("Adding new pet: {}", request);

        if (request.getName() == null || request.getName().trim().isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Pet name is required");
        }

        if (request.getType() == null || request.getType().trim().isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Pet type is required");
        }

        String status = (request.getStatus() == null || request.getStatus().trim().isEmpty()) ? "available" : request.getStatus();

        long newId = generatePetId();
        Pet pet = new Pet(newId, request.getName(), request.getType(), status);
        pets.put(newId, pet);

        logger.info("New pet added with id {}", newId);

        Map<String, Object> response = new HashMap<>();
        response.put("id", newId);
        response.put("message", "New pet added successfully");
        return response;
    }

    /**
     * POST /pets/{id}/status
     * Update status of a pet.
     */
    @PostMapping(value = "/{id}/status", consumes = MediaType.APPLICATION_JSON_VALUE, produces = MediaType.APPLICATION_JSON_VALUE)
    public Map<String, Object> updatePetStatus(@PathVariable("id") long id, @RequestBody StatusUpdateRequest request) {
        logger.info("Updating status of pet id {} to {}", id, request.getStatus());

        Pet pet = pets.get(id);
        if (pet == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Pet not found");
        }

        if (request.getStatus() == null || request.getStatus().trim().isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Status is required");
        }

        pet.setStatus(request.getStatus());
        pets.put(id, pet);

        // TODO: Fire-and-forget event workflow for pet status change (e.g., notification)
        CompletableFuture.runAsync(() -> {
            logger.info("Processing event workflow for pet id {} status change to {}", id, request.getStatus());
            // Placeholder for event workflow logic
        });

        Map<String, Object> response = new HashMap<>();
        response.put("id", id);
        response.put("message", "Pet status updated successfully");
        return response;
    }

    /**
     * GET /pets/fun/fact
     * Return a random pet fact.
     */
    @GetMapping(value = "/fun/fact", produces = MediaType.APPLICATION_JSON_VALUE)
    public Map<String, String> randomPetFact() {
        int index = new Random().nextInt(petFacts.size());
        String fact = petFacts.get(index);
        logger.info("Returning random pet fact: {}", fact);
        return Collections.singletonMap("fact", fact);
    }

    // Helper to generate pet IDs (simple sequence)
    private synchronized long generatePetId() {
        return petIdSequence++;
    }

    // Exception handler for ResponseStatusException
    @ExceptionHandler(ResponseStatusException.class)
    @ResponseStatus
    public Map<String, Object> handleResponseStatusException(ResponseStatusException ex) {
        logger.error("Handled error: {}", ex.getReason());
        Map<String, Object> error = new HashMap<>();
        error.put("status", ex.getStatusCode().value());
        error.put("error", ex.getStatusCode().getReasonPhrase());
        error.put("message", ex.getReason());
        return error;
    }

    // --- DTOs and Models ---

    @Data
    public static class FetchFilter {
        private String status;
    }

    @Data
    @AllArgsConstructor
    @NoArgsConstructor
    public static class Pet {
        private long id;
        private String name;
        private String type;
        private String status;
    }

    @Data
    public static class PetCreateRequest {
        private String name;
        private String type;
        private String status;
    }

    @Data
    public static class StatusUpdateRequest {
        private String status;
    }
}
```