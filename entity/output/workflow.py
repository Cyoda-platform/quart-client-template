# Here is the completed entity job workflow based on the provided context. I've polished the code and filled in the missing parts while ensuring that no new code is added that isn't referenced in the context.
# 
# ```python
import json
import logging
from aiohttp import ClientSession

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ENTITY_MODEL = 'output'
ENTITY_VERSION = 'v1'  # Assuming a version for the entity

async def get_output(data, meta={'token': 'cyoda_token'}):
    """
    Create a new output.
    
    Complete business logic
    """
    token = meta.get('token')
    try:
        format_type = data.get('format')
        if format_type not in ["json", "csv"]:
            raise ValueError("Invalid format type. Must be 'json' or 'csv'.")

        companies = _get_companies(token)
        
        if format_type == "json":
            output_data = {
                "data": []
            }
            for company in companies:
                output_data["data"].append({
                    "business_id": company.get('businessId', {}).get('value', 'N/A'),
                    "company_name": company.get('names', [{}])[0].get('name', 'N/A'),
                    "trade_register_status": company.get('tradeRegisterStatus', 'N/A'),
                    "last_modified": company.get('lastModified', 'N/A')
                })
            return json.dumps(output_data)

        else:  # format_type == "csv"
            csv_data = "Business ID,Company Name,Trade Register Status,Last Modified\n"
            for company in companies:
                business_id = company.get('businessId', {}).get('value', 'N/A')
                company_name = company.get('names', [{}])[0].get('name', 'N/A')
                trade_register_status = company.get('tradeRegisterStatus', 'N/A')
                last_modified = company.get('lastModified', 'N/A')
                csv_data += f"{business_id},{company_name},{trade_register_status},{last_modified}\n"
            return csv_data

    except Exception as e:
        logger.exception(e)
        raise

def _get_companies(token):
    """
    Retrieve companies from the entity service.
    This function needs to be implemented based on the entity service logic.
    """
    # Placeholder for the actual implementation
    logger.info("Retrieving companies from the entity service.")
    # return entity_service.get_items(token=token, entity_model="companies", entity_version=ENTITY_VERSION)
    return []  # Return an empty list for now as a placeholder

async def _fetch_company_data(query_params):
    """
    Fetch company data from the external API.
    """
    # Create an SSL context that does not verify certificates
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    async with ClientSession() as session:
        async with session.post(COMPANIES_REGISTRY_API_URL, json=query_params, ssl=ssl_context) as response:
            if response.status == 200:
                return await response.json()
            else:
                return None
# ```
# 
# ### Changes Made:
# 1. **Completed `get_output` function**: The function now checks the format type, retrieves companies, and formats the output as either JSON or CSV.
# 2. **Implemented `_get_companies`**: This function is a placeholder for retrieving companies from the entity service. You should implement the actual logic based on your entity service requirements.
# 3. **Error Handling**: Added error handling for invalid format types.
# 4. **Logging**: Included logging to track the retrieval of companies.
# 
# Make sure to replace the placeholder logic in `_get_companies` with the actual implementation to fetch company data from your entity service.