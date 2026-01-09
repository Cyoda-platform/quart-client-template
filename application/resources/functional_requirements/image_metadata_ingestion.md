# Image + Metadata Ingestion Requirements

Project: Cats API Ingestion & Analytics
Focus: Download original images and generate thumbnails; store metadata for analytics.

1. Purpose

Collect images and metadata from the Cats API to enable analytics such as breed popularity, image counts over time, and basic image-based features.

2. Functional Requirements

- Poll the Cats API's images endpoint every 5 minutes by default; adjustable via configuration.
- For each image record:
  - Download the original image file and save to object storage with a structured path: /images/{year}/{month}/{day}/{image_id}.jpg
  - Create a thumbnail (max dimension 300px) and save to object storage at /images/thumbnails/{year}/{month}/{day}/{image_id}_thumb.jpg
  - Persist metadata in the application database with fields: id, url, breed_id, width, height, download_timestamp, storage_path_original, storage_path_thumbnail, content_hash
- Handle retries with exponential backoff for failed downloads (max 5 retries).
- Skip duplicate images by checking content_hash before storing.
- Log success/fail stats for each ingestion run and expose a simple metrics endpoint.

3. Non-functional Requirements

- Storage: Use Cyoda-managed object storage (configured via environment variables).
- Concurrency: Support parallel downloads (configurable worker pool; default 4 workers).
- Security: Store any secrets in the environment or Cyoda secret manager; do not commit secrets to the repository.
- Observability: Emit basic metrics (images_ingested, images_failed, avg_download_time) and structured logs.
- Retention: Keep originals and thumbnails for 365 days, configurable.

4. Acceptance Criteria

- Running the ingestion job results in originals and thumbnails stored in object storage and metadata persisted.
- Duplicate images are not stored twice.
- Thumbnails are correctly sized and retrievable.
- Metrics show accurate counts for a sample ingestion run.

5. Next Steps

- Define Entities: Image, Breed, IngestionRun
- Design Workflows: ImageIngestion workflow (download -> thumbnail -> persist)
- Implement processors and storage adapters

