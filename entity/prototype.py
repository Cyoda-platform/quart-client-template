# Here's the updated `prototype.py` code that changes the GET requests to POST requests for both the `/companies` and `/output` endpoints. This change requires you to send the necessary parameters in the body of the POST request instead of as query parameters.
# 
# ### Updated `prototype.py`
# 
# ```python
from quart import Quart, request, jsonify
from quart_schema import QuartSchema
import aiohttp
import ssl

app = Quart(__name__)
QuartSchema(app)

# Local cache to simulate persistence
local_cache = {}

# Constants for the Open Data YTJ API
COMPANIES_REGISTRY_API_URL = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"

async def fetch_company_data(query_params):
    # Create an SSL context that does not verify certificates
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    async with aiohttp.ClientSession() as session:
        async with session.post(COMPANIES_REGISTRY_API_URL, json=query_params, ssl=ssl_context) as response:
            if response.status == 200:
                return await response.json()
            else:
                return None

@app.route('/companies', methods=['POST'])
async def get_companies():
    # Collect JSON body parameters
    request_data = await request.get_json()

    query_params = {
        'name': request_data.get('name'),
        'location': request_data.get('location'),
        'businessId': request_data.get('businessId'),
        'companyForm': request_data.get('companyForm'),
        'mainBusinessLine': request_data.get('mainBusinessLine'),
        'registrationDateStart': request_data.get('registrationDateStart'),
        'registrationDateEnd': request_data.get('registrationDateEnd'),
        'postCode': request_data.get('postCode'),
        'businessIdRegistrationStart': request_data.get('businessIdRegistrationStart'),
        'businessIdRegistrationEnd': request_data.get('businessIdRegistrationEnd'),
        'page': request_data.get('page'),
    }

    # Filter out None values from query_params
    filtered_params = {k: v for k, v in query_params.items() if v is not None}

    # Fetch company data
    company_data = await fetch_company_data(filtered_params)
    if not company_data or 'companies' not in company_data:
        return jsonify({"error": "No companies found"}), 404

    # Cache the company data locally
    for company in company_data['companies']:
        local_cache[company['businessId']['value']] = company

    return jsonify(company_data)

@app.route('/output', methods=['POST'])
async def get_output():
    request_data = await request.get_json()
    format_type = request_data.get('format')

    if format_type not in ["json", "csv"]:
        return jsonify({"error": "Invalid format. Use 'json' or 'csv'."}), 400

    # Generate output based on local_cache
    if format_type == "json":
        return jsonify(list(local_cache.values()))
    else:
        # Generate CSV output
        csv_data = "Business ID,Company Name,Trade Register Status,Last Modified\n"
        for company in local_cache.values():
            business_id = company.get('businessId', {}).get('value', 'N/A')
            company_name = company.get('names', [{}])[0].get('name', 'N/A')
            trade_register_status = company.get('tradeRegisterStatus', 'N/A')
            last_modified = company.get('lastModified', 'N/A')

            csv_data += f"{business_id},{company_name},{trade_register_status},{last_modified}\n"
        
        return csv_data, 200, {'Content-Type': 'text/csv'}

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
# ```
# 
# ### Key Changes:
# 1. **POST Requests**:
#    - Both the `/companies` and `/output` endpoints now accept POST requests. The parameters are expected to be sent in the JSON body of the request.
#    - The `fetch_company_data` function uses `session.post` to send a POST request to the external API.
# 
# 2. **Request Body**:
#    - The parameters for querying companies and the format for output are taken from the JSON body of the request instead of query parameters.
# 
# ### Testing with `curl`
# 
# To test the `/companies` endpoint using `curl` with a POST request, you can use the following command:
# 
# ```bash
# curl -X POST "http://localhost:8000/companies" -H "Content-Type: application/json" -d '{"name": "Example Company", "location": "Helsinki"}'
# ```
# 
# And to test the `/output` endpoint for CSV format, use this command:
# 
# ```bash
# curl -X POST "http://localhost:8000/output" -H "Content-Type: application/json" -d '{"format": "csv"}'
# ```
# 
# These commands will allow you to test the API endpoints effectively. Let me know if you need further adjustments or assistance!