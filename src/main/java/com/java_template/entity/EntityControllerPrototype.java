package com.java_template.entity;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.MediaType;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.server.ResponseStatusException;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import java.util.*;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Validated
@RestController
@RequestMapping("/pets")
public class EntityControllerPrototype {

    private static final Logger logger = LoggerFactory.getLogger(EntityControllerPrototype.class);
    private final RestTemplate restTemplate = new RestTemplate();
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final Map<Long, Pet> pets = new ConcurrentHashMap<>();
    private long petIdSequence = 1;
    private final List<String> petFacts = Arrays.asList(
        "Cats sleep for 70% of their lives.",
        "Dogs have three eyelids.",
        "A group of cats is called a clowder.",
        "Rabbits can see behind them without turning their heads."
    );
    private static final String PETSTORE_API_BASE = "https://petstore.swagger.io/v2";

    @PostMapping(value = "/fetch", consumes = MediaType.APPLICATION_JSON_VALUE, produces = MediaType.APPLICATION_JSON_VALUE)
    public Map<String, Object> fetchPets(@Valid @RequestBody(required = false) FetchFilter filter) {
        logger.info("Fetching pets with filter {}", filter);
        String statusFilter = filter != null ? filter.getStatus() : "";
        String url = PETSTORE_API_BASE + "/pet/findByStatus?status=" + statusFilter;
        try {
            String json = restTemplate.getForObject(url, String.class);
            JsonNode root = objectMapper.readTree(json);
            if (!root.isArray()) {
                throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "Unexpected format");
            }
            int count = 0;
            for (JsonNode node : root) {
                long id = node.path("id").asLong(-1);
                if (id < 0) continue;
                String name = node.path("name").asText("Unnamed");
                String status = node.path("status").asText("unknown");
                String type = node.path("category").path("name").asText("Unknown");
                pets.put(id, new Pet(id, name, type, status));
                count++;
            }
            Map<String, Object> resp = new HashMap<>();
            resp.put("message", "Pets data fetched and updated successfully");
            resp.put("count", count);
            return resp;
        } catch (Exception e) {
            logger.error("Error fetching pets", e);
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "Failed to fetch pets");
        }
    }

    @GetMapping(produces = MediaType.APPLICATION_JSON_VALUE)
    public List<Pet> listPets(@RequestParam(required = false) @Pattern(regexp = "available|pending|sold", message = "Invalid status") String status) {
        logger.info("Listing pets with status {}", status);
        if (status == null || status.isEmpty()) {
            return new ArrayList<>(pets.values());
        }
        List<Pet> result = new ArrayList<>();
        for (Pet p : pets.values()) {
            if (status.equalsIgnoreCase(p.getStatus())) {
                result.add(p);
            }
        }
        return result;
    }

    @PostMapping(consumes = MediaType.APPLICATION_JSON_VALUE, produces = MediaType.APPLICATION_JSON_VALUE)
    public Map<String, Object> addPet(@Valid @RequestBody PetCreateRequest req) {
        logger.info("Adding pet {}", req);
        long id = generatePetId();
        String status = req.getStatus() == null ? "available" : req.getStatus();
        pets.put(id, new Pet(id, req.getName(), req.getType(), status));
        Map<String, Object> resp = new HashMap<>();
        resp.put("id", id);
        resp.put("message", "New pet added successfully");
        return resp;
    }

    @PostMapping(value = "/{id}/status", consumes = MediaType.APPLICATION_JSON_VALUE, produces = MediaType.APPLICATION_JSON_VALUE)
    public Map<String, Object> updatePetStatus(
        @PathVariable long id,
        @Valid @RequestBody StatusUpdateRequest req
    ) {
        logger.info("Updating status for pet {} to {}", id, req.getStatus());
        Pet pet = pets.get(id);
        if (pet == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Pet not found");
        }
        pet.setStatus(req.getStatus());
        CompletableFuture.runAsync(() -> {
            logger.info("Async workflow for pet {} status {}", id, req.getStatus());
            // TODO: event-driven logic
        });
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

    private synchronized long generatePetId() {
        return petIdSequence++;
    }

    @ExceptionHandler(ResponseStatusException.class)
    @ResponseStatus
    public Map<String, Object> handleError(ResponseStatusException ex) {
        logger.error("Error: {}", ex.getReason());
        Map<String, Object> err = new HashMap<>();
        err.put("status", ex.getStatusCode().value());
        err.put("error", ex.getStatusCode().getReasonPhrase());
        err.put("message", ex.getReason());
        return err;
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
}