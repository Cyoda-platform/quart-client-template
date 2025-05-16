package com.java_template.entity;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.scheduling.annotation.Async;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.server.ResponseStatusException;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@RestController
@Validated
@RequestMapping("/pets")
public class EntityControllerPrototype {

    private static final Logger logger = LoggerFactory.getLogger(EntityControllerPrototype.class);
    private static final String PETSTORE_API_BASE = "https://petstore.swagger.io/v2";
    private final RestTemplate restTemplate = new RestTemplate();
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final Map<Long, Pet> petStore = new ConcurrentHashMap<>();

    @PostMapping
    public ResponseEntity<PetResponse> addOrUpdatePet(@RequestBody @Valid PetRequest request) {
        logger.info("POST /pets action={}", request.getAction());
        switch (request.getAction()) {
            case "fetch":
                if (request.getId() == null) {
                    throw new ResponseStatusException(ResponseStatusException.Status.REQUESTED_RANGE_NOT_SATISFIABLE, "id required");
                }
                Pet fetched = fetchPet(request.getId());
                petStore.put(fetched.getId(), fetched);
                return ResponseEntity.ok(new PetResponse(true, fetched));
            case "add":
                Pet newPet = new Pet();
                newPet.setId(request.getId() != null ? request.getId() : generateId());
                newPet.setName(request.getName());
                newPet.setCategory(request.getCategory());
                newPet.setStatus(request.getStatus());
                petStore.put(newPet.getId(), newPet);
                return ResponseEntity.ok(new PetResponse(true, newPet));
            case "update":
                if (request.getId() == null || !petStore.containsKey(request.getId())) {
                    throw new ResponseStatusException(ResponseStatusException.Status.NOT_FOUND, "id not found");
                }
                Pet upd = petStore.get(request.getId());
                upd.setName(request.getName());
                upd.setCategory(request.getCategory());
                upd.setStatus(request.getStatus());
                return ResponseEntity.ok(new PetResponse(true, upd));
            default:
                throw new ResponseStatusException(ResponseStatusException.Status.BAD_REQUEST, "unknown action");
        }
    }

    @PostMapping("/search")
    public ResponseEntity<SearchResponse> searchPets(@RequestBody @Valid SearchRequest req) {
        logger.info("POST /pets/search filters={}", req);
        List<Pet> list = new ArrayList<>();
        if (req.getStatus() != null) {
            String url = PETSTORE_API_BASE + "/pet/findByStatus?status=" + req.getStatus();
            String resp = restTemplate.getForObject(url, String.class);
            try {
                JsonNode arr = objectMapper.readTree(resp);
                if (arr.isArray()) {
                    for (JsonNode node : arr) {
                        Pet p = jsonToPet(node);
                        if (matches(p, req.getCategory(), req.getName())) {
                            petStore.put(p.getId(), p);
                            list.add(p);
                        }
                    }
                }
            } catch (Exception e) {
                throw new ResponseStatusException(ResponseStatusException.Status.INTERNAL_SERVER_ERROR, "external error");
            }
        } else {
            for (Pet p : petStore.values()) {
                if (matches(p, req.getCategory(), req.getName())) list.add(p);
            }
        }
        return ResponseEntity.ok(new SearchResponse(list));
    }

    @GetMapping("/{id}")
    public ResponseEntity<Pet> getPet(@PathVariable Long id) {
        logger.info("GET /pets/{}", id);
        Pet p = petStore.get(id);
        if (p == null) {
            throw new ResponseStatusException(ResponseStatusException.Status.NOT_FOUND, "not found");
        }
        return ResponseEntity.ok(p);
    }

    private Pet fetchPet(Long id) {
        try {
            String body = restTemplate.getForObject(PETSTORE_API_BASE + "/pet/" + id, String.class);
            return jsonToPet(objectMapper.readTree(body));
        } catch (Exception e) {
            throw new ResponseStatusException(ResponseStatusException.Status.INTERNAL_SERVER_ERROR, "fetch failed");
        }
    }

    private Pet jsonToPet(JsonNode n) {
        Pet p = new Pet();
        p.setId(n.has("id") ? n.get("id").asLong() : null);
        p.setName(n.has("name") ? n.get("name").asText() : null);
        p.setCategory(n.has("category") && n.get("category").has("name")
                ? n.get("category").get("name").asText() : null);
        p.setStatus(n.has("status") ? n.get("status").asText() : null);
        return p;
    }

    private boolean matches(Pet p, String cat, String nm) {
        if (cat != null && !cat.equalsIgnoreCase(p.getCategory())) return false;
        if (nm != null && (p.getName() == null || !p.getName().toLowerCase().contains(nm.toLowerCase())))
            return false;
        return true;
    }

    private Long generateId() {
        return new Random().nextLong() & Long.MAX_VALUE;
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
    }

    @ExceptionHandler(ResponseStatusException.class)
    public ResponseEntity<Map<String, String>> onError(ResponseStatusException ex) {
        Map<String, String> err = new HashMap<>();
        err.put("error", ex.getReason());
        return ResponseEntity.status(ex.getStatusCode()).body(err);
    }
}