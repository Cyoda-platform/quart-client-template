import requests
import json

# Example entity structure for raw data
class RawDataEntity:
    def __init__(self, data_id, title, due_date, completed):
        self.data_id = data_id
        self.title = title
        self.due_date = due_date
        self.completed = completed

    def to_json(self):
        return {
            "data_id": self.data_id,
            "title": self.title,
            "due_date": self.due_date,
            "completed": self.completed
        }

def ingest_data(api_url):
    """
    Fetch data from the external data source and process it into the RawDataEntity structure.
    
    Parameters:
    - api_url: URL of the external API endpoint to fetch data from.
    
    Returns:
    - List of RawDataEntity objects if mapping is successful.
    - Otherwise, return the raw data as is.
    """
    response = requests.get(api_url)
    
    if response.status_code != 200:
        print(f"Error fetching data: {response.status_code}")
        return None
    
    raw_data = response.json()
    processed_data = []

    for item in raw_data:
        try:
            # Map the raw data to the RawDataEntity structure
            entity = RawDataEntity(
                data_id=item.get("id"),
                title=item.get("title"),
                due_date=item.get("dueDate"),
                completed=item.get("completed")
            )
            processed_data.append(entity.to_json())
        except Exception as e:
            print(f"Error processing item {item}: {e}")

    return processed_data

# Example test cases
if __name__ == "__main__":
    # Test the ingest_data function
    test_api_url = "https://fakerestapi.azurewebsites.net/api/v1/Activities"
    processed_data = ingest_data(test_api_url)

    if processed_data:
        print("Processed Data:")
        print(json.dumps(processed_data, indent=2))
    else:
        print("No data processed.")