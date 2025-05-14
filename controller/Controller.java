package com.java_template.entity;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.java_template.common.service.EntityService;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.eclipse.microprofile.rest.client.inject.RestClient;
import org.jboss.resteasy.annotations.jaxrs.PathParam;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import java.util.*;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;

@Path("/cyoda-pets")
@ApplicationScoped
public class CyodaEntityControllerPrototype {

    private static final Logger logger = LoggerFactory.getLogger(CyodaEntityControllerPrototype.class);
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final EntityService entityService;
    private static final String ENTITY_NAME = "Pet";
    private static final String ENTITY_VERSION = "v1"; // Assuming ENTITY_VERSION is needed as in original
    private final List<String> petFacts = Arrays.asList(
            "Cats sleep for 70% of their lives.",
            "Dogs have three eyelids.",
            "A group of cats is called a clowder.",
            "Rabbits can see behind them without turning their heads."
    );
    private static final String PETSTORE_API_BASE = "https://petstore.swagger.io/v2";

    @Inject
    public CyodaEntityControllerPrototype(EntityService entityService) {
        this.entityService = entityService;
    }

    @POST
    @Path("/fetch")
    @Consumes(MediaType.APPLICATION_JSON)
    @Produces(MediaType.APPLICATION_JSON)
    public Response fetchPets(@Valid FetchFilter filter) throws ExecutionException, InterruptedException {
        logger.info("Fetching pets with filter {}", filter);
        String statusFilter = filter != null ? filter.getStatus() : "";
        String url = PETSTORE_API_BASE + "/pet/findByStatus?status=" + statusFilter;

        // Using java.net.HttpURLConnection for fetching external API as no RestTemplate in Jakarta EE
        String json;
        try {
            json = java.net.http.HttpClient.newHttpClient()
                    .send(java.net.http.HttpRequest.newBuilder(java.net.URI.create(url)).GET().build(), java.net.http.HttpResponse.BodyHandlers.ofString())
                    .body();
        } catch (Exception e) {
            logger.error("Error fetching from petstore", e);
            return Response.status(Response.Status.BAD_GATEWAY).entity(Map.of("error", "Failed to fetch from petstore")).build();
        }

        JsonNode root;
        try {
            root = objectMapper.readTree(json);
        } catch (Exception e) {
            logger.error("Error parsing JSON from petstore", e);
            return Response.status(Response.Status.BAD_GATEWAY).entity(Map.of("error", "Unexpected format")).build();
        }
        if (!root.isArray()) {
            return Response.status(Response.Status.BAD_GATEWAY).entity(Map.of("error", "Unexpected format")).build();
        }

        List<CompletableFuture<UUID>> addFutures = new ArrayList<>();
        int count = 0;
        for (JsonNode node : root) {
            long id = node.path("id").asLong(-1);
            if (id < 0) continue;
            ObjectNode petNode = objectMapper.createObjectNode();
            petNode.put("id", id);
            petNode.put("name", node.path("name").asText("Unnamed"));
            petNode.put("status", node.path("status").asText("unknown"));
            petNode.put("type", node.path("category").path("name").asText("Unknown"));

            addFutures.add(entityService.addItem(ENTITY_NAME, ENTITY_VERSION, petNode));
            count++;
        }

        for (CompletableFuture<UUID> future : addFutures) {
            future.get();
        }
        Map<String, Object> resp = new HashMap<>();
        resp.put("message", "Pets data fetched and updated successfully");
        resp.put("count", count);
        return Response.ok(resp).build();
    }

    @GET
    @Produces(MediaType.APPLICATION_JSON)
    public Response listPets(@QueryParam("status") @Pattern(regexp = "available|pending|sold", message = "Invalid status") String status) throws ExecutionException, InterruptedException {
        logger.info("Listing pets with status {}", status);
        CompletableFuture<ArrayNode> itemsFuture;
        if (status == null || status.isEmpty()) {
            itemsFuture = entityService.getItems(ENTITY_NAME, ENTITY_VERSION);
        } else {
            String condition = String.format("status='%s'", status);
            itemsFuture = entityService.getItemsByCondition(ENTITY_NAME, ENTITY_VERSION, condition);
        }
        ArrayNode items = itemsFuture.get();
        List<Pet> result = new ArrayList<>();
        for (JsonNode item : items) {
            long technicalId = item.path("technicalId").asLong(-1);
            if (technicalId < 0) continue;
            String name = item.path("name").asText("Unnamed");
            String type = item.path("type").asText("Unknown");
            String petStatus = item.path("status").asText("unknown");
            if (status == null || status.isEmpty() || status.equalsIgnoreCase(petStatus)) {
                result.add(new Pet(technicalId, name, type, petStatus));
            }
        }
        return Response.ok(result).build();
    }

    @POST
    @Consumes(MediaType.APPLICATION_JSON)
    @Produces(MediaType.APPLICATION_JSON)
    public Response addPet(@Valid PetCreateRequest req) throws ExecutionException, InterruptedException {
        logger.info("Adding pet {}", req);
        ObjectNode petNode = objectMapper.createObjectNode();
        petNode.put("name", req.getName());
        petNode.put("type", req.getType());
        if (req.getStatus() != null && !req.getStatus().isEmpty()) {
            petNode.put("status", req.getStatus());
        }

        CompletableFuture<UUID> idFuture = entityService.addItem(ENTITY_NAME, ENTITY_VERSION, petNode);
        UUID technicalId = idFuture.get();
        Map<String, Object> resp = new HashMap<>();
        resp.put("id", technicalId.toString());
        resp.put("message", "New pet added successfully");
        return Response.ok(resp).build();
    }

    @POST
    @Path("/{id}/status")
    @Consumes(MediaType.APPLICATION_JSON)
    @Produces(MediaType.APPLICATION_JSON)
    public Response updatePetStatus(@PathParam("id") String id, @Valid StatusUpdateRequest req) throws ExecutionException, InterruptedException {
        logger.info("Updating status for pet {} to {}", id, req.getStatus());
        UUID technicalId;
        try {
            technicalId = UUID.fromString(id);
        } catch (IllegalArgumentException e) {
            return Response.status(Response.Status.BAD_REQUEST).entity(Map.of("error", "Invalid pet id format")).build();
        }
        CompletableFuture<ObjectNode> itemFuture = entityService.getItem(ENTITY_NAME, ENTITY_VERSION, technicalId);
        ObjectNode existingItem = itemFuture.get();
        if (existingItem == null || existingItem.isEmpty()) {
            return Response.status(Response.Status.NOT_FOUND).entity(Map.of("error", "Pet not found")).build();
        }

        existingItem.put("status", req.getStatus());

        CompletableFuture<UUID> updatedItemId = entityService.updateItem(ENTITY_NAME, ENTITY_VERSION, technicalId, existingItem);
        updatedItemId.get();

        Map<String, Object> resp = new HashMap<>();
        resp.put("id", id);
        resp.put("message", "Pet status updated successfully");
        return Response.ok(resp).build();
    }

    @GET
    @Path("/fun/fact")
    @Produces(MediaType.APPLICATION_JSON)
    public Response randomPetFact() {
        String fact = petFacts.get(new Random().nextInt(petFacts.size()));
        logger.info("Random pet fact: {}", fact);
        return Response.ok(Collections.singletonMap("fact", fact)).build();
    }

    private boolean isValidStatus(String status) {
        return "available".equalsIgnoreCase(status) || "pending".equalsIgnoreCase(status) || "sold".equalsIgnoreCase(status);
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

    @Data
    @AllArgsConstructor
    public static class Pet {
        private long technicalId; // corresponds to unique id from entityService
        private String name;
        private String type;
        private String status;
    }
}