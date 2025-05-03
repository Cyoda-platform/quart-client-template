import glob
import importlib.util
import inspect
import os
import entity

process_dispatch = {}

def find_and_import_workflows():
    entity_path = entity.__path__[0]
    # Pattern to match 'entity/*/workflow/workflow.py'
    pattern = os.path.join(entity_path, '*', 'workflow.py')
    for module_path in glob.glob(pattern):
        # Compute the module name
        # Example: if module_path is '/path/to/entity/any_name/workflow/workflow.py'
        # The module name should be 'entity.any_name.workflow.workflow'
        relative_path = os.path.relpath(module_path, entity_path)
        module_name = entity.__name__ + '.' + relative_path.replace(os.sep, '.')[:-3]  # Remove '.py' extension
        try:
            # Import the module from the file path
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                # Collect all functions that don't start with an underscore
                for name, func in inspect.getmembers(module, inspect.isfunction):
                    if not name.startswith("_"):
                        process_dispatch[name] = func
        except Exception as e:
            print(f"Error importing module {module_name}: {e}")

# Run the function to populate process_dispatch
find_and_import_workflows()

#data={'entityId': 'ee965a32-4df6-11b2-b48d-f20bdf753a91', 'id': 'e37b9e72-c7b4-4ed3-9fa7-85ab6d85e4b1', 'payload': {'data': {'data_source': {'data_retrieval_method': 'GET', 'source_name': 'External API', 'source_url': 'https://api.example.com/data'}, 'job_id': 'job_001', 'job_name': 'Data Processing Job', 'recipients': [{'email': 'admin@example.com', 'name': 'Admin User'}, {'email': 'analyst@example.com', 'name': 'Data Analyst'}], 'report': {'distribution_info': {'communication_method': 'Email', 'sent_at': '2023-10-01T17:40:00Z'}, 'generated_at': '2023-10-01T17:35:00Z', 'report_id': 'report_001', 'report_title': 'Monthly Data Processing Report'}, 'request_parameters': {'code': '7080005051286', 'country': 'FI', 'name': ''}}, 'type': 'TREE'}, 'processorId': '1fbb8b6e-c2c7-11ef-a99c-ce3d8f1a57a3', 'processorName': 'ingest_raw_data', 'requestId': 'e37b9e72-c7b4-4ed3-9fa7-85ab6d85e4b1', 'success': True, 'transactionId': 'bb537de0-c2f2-11ef-b48d-f20bdf753a91', 'warnings': []}
#processor_name='ingest_raw_data'
async def process_event(data, processor_name):
    payload_data = data['payload']['data']
    if processor_name in process_dispatch:
        #todo
        response = await process_dispatch[processor_name](payload_data)
    else:
        raise ValueError(f"Unknown processing step: {processor_name}")
    return response
