package com.java_template.entity;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
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

    private final RestTemplate restTemplate = new RestTemplate();
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final Map<Long, Pet> petStore = new ConcurrentHashMap<>();
    private long idCounter = 1L;
    private static final String PETSTORE_API_BASE = "https://petstore.swagger.io/v2";

    @PostMapping("/search")
    public ResponseEntity<PetsResponse> searchPets(@RequestBody @Valid PetSearchRequest request) {
        log.info("Received search request: {}", request);
        try {
            String statusParam = request.getStatus() == null || request.getStatus().isBlank() ? "available" : request.getStatus();
            String url = PETSTORE_API_BASE + "/pet/findByStatus?status=" + statusParam;
            log.info("Calling Petstore API: {}", url);
            String responseStr = restTemplate.getForObject(url, String.class);
            JsonNode root = objectMapper.readTree(responseStr);
            List<Pet> matchedPets = new ArrayList<>();
            if (root.isArray()) {
                for (JsonNode petNode : root) {
                    Pet pet = fromPetstoreJson(petNode);
                    if (matchesFilters(pet, request)) matchedPets.add(pet);
                }
            }
            return ResponseEntity.ok(new PetsResponse(matchedPets));
        } catch (Exception ex) {
            log.error("Error searching pets", ex);
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "Failed to search pets");
        }
    }

    @PostMapping("/add")
    public ResponseEntity<AddPetResponse> addPet(@RequestBody @Valid PetAddRequest request) {
        log.info("Adding new pet: {}", request);
        long newId = generateId();
        Pet pet = new Pet(newId, request.getName(), request.getCategory(), request.getStatus(),
                request.getPhotoUrls(), request.getTags());
        petStore.put(newId, pet);
        CompletableFuture.runAsync(() -> log.info("Background processing for pet id {}", newId));
        return ResponseEntity.ok(new AddPetResponse(newId, "Pet added successfully"));
    }

    @GetMapping("/{id}")
    public ResponseEntity<Pet> getPetById(@PathVariable("id") Long id) {
        log.info("Retrieving pet by id: {}", id);
        Pet pet = petStore.get(id);
        if (pet == null) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Pet not found");
        return ResponseEntity.ok(pet);
    }

    @PostMapping("/update/{id}")
    public ResponseEntity<MessageResponse> updatePet(
            @PathVariable("id") Long id,
            @RequestBody @Valid PetUpdateRequest request) {
        log.info("Updating pet id {} with data {}", id, request);
        Pet existingPet = petStore.get(id);
        if (existingPet == null) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Pet not found");
        if (request.getName() != null) existingPet.setName(request.getName());
        if (request.getCategory() != null) existingPet.setCategory(request.getCategory());
        if (request.getStatus() != null) existingPet.setStatus(request.getStatus());
        if (request.getPhotoUrls() != null) existingPet.setPhotoUrls(request.getPhotoUrls());
        if (request.getTags() != null) existingPet.setTags(request.getTags());
        petStore.put(id, existingPet);
        CompletableFuture.runAsync(() -> log.info("Background update processing for pet id {}", id));
        return ResponseEntity.ok(new MessageResponse("Pet updated successfully"));
    }

    @GetMapping("/list")
    public ResponseEntity<PetsResponse> listPets(
            @RequestParam(required = false) @Size(max = 50) String category,
            @RequestParam(required = false) @Pattern(regexp = "available|pending|sold") String status) {
        log.info("Listing pets with filters: category={}, status={}", category, status);
        List<Pet> filteredPets = new ArrayList<>();
        for (Pet pet : petStore.values()) {
            boolean matches = true;
            if (category != null && !category.isBlank()) matches &= category.equalsIgnoreCase(pet.getCategory());
            if (status != null && !status.isBlank()) matches &= status.equalsIgnoreCase(pet.getStatus());
            if (matches) filteredPets.add(pet);
        }
        return ResponseEntity.ok(new PetsResponse(filteredPets));
    }

    private boolean matchesFilters(Pet pet, PetSearchRequest filters) {
        if (filters.getCategory() != null && !filters.getCategory().isBlank()) {
            if (!filters.getCategory().equalsIgnoreCase(pet.getCategory())) return false;
        }
        if (filters.getStatus() != null && !filters.getStatus().isBlank()) {
            if (!filters.getStatus().equalsIgnoreCase(pet.getStatus())) return false;
        }
        if (filters.getName() != null && !filters.getName().isBlank()) {
            if (pet.getName() == null || !pet.getName().toLowerCase().contains(filters.getName().toLowerCase())) return false;
        }
        return true;
    }

    private Pet fromPetstoreJson(JsonNode petNode) {
        Long id = petNode.has("id") && petNode.get("id").canConvertToLong() ? petNode.get("id").longValue() : null;
        String name = petNode.path("name").asText(null);
        String status = petNode.path("status").asText(null);
        String category = petNode.path("category").path("name").asText(null);
        List<String> photoUrls = new ArrayList<>();
        petNode.path("photoUrls").forEach(urlNode -> photoUrls.add(urlNode.asText()));
        List<String> tags = new ArrayList<>();
        petNode.path("tags").forEach(tagNode -> tags.add(tagNode.path("name").asText()));
        return new Pet(id, name, category, status, photoUrls, tags);
    }

    private synchronized long generateId() {
        return idCounter++;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    static class Pet {
        private Long id;
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
        private Long id;
        private String message;
    }

    @Data
    @AllArgsConstructor
    static class MessageResponse {
        private String message;
    }

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