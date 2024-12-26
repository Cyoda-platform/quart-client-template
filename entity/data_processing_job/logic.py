from common.app_init import entity_service


def data_processing_job_scheduler(token: str) -> None:
    data = {}  # Initialize with necessary data
    entity_service.add_item(
        token, "data_processing_job", "1.0", data
    )  # Save job entity with data model $data to cyoda
