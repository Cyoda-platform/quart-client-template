{
    "entity_name": "raw_data_entity",
    "entity_type": "EXTERNAL_SOURCES_PULL_BASED_RAW_DATA",
    "entity_source": "ENTITY_EVENT",
    "depends_on_entity": "data_ingestion_job",
    "entity_workflow": {
        "name": "raw_data_entity_workflow",
        "class_name": "com.cyoda.tdb.model.treenode.TreeNodeEntity",
        "transitions": []
    }
}