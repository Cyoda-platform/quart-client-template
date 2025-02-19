# The error you are encountering is due to the presence of `None` values in the `query_params` dictionary when making the GET request. When you pass these parameters to the aiohttp request, it raises a `TypeError` because aiohttp expects all query parameter values to be strings, integers, or floats.
# 
# To resolve this issue, you can filter out any query parameters that have `None` values before making the request. Here’s an updated version of the `prototype.py` file with this fix:
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
        async with session.get(COMPANIES_REGISTRY_API_URL, params=query_params, ssl=ssl_context) as response:
            if response.status == 200:
                return await response.json()
            else:
                return None

@app.route('/companies', methods=['GET'])
async def get_companies():
    # Collect query parameters
    query_params = {
        'name': request.args.get('name'),
        'location': request.args.get('location'),
        'businessId': request.args.get('businessId'),
        'companyForm': request.args.get('companyForm'),
        'mainBusinessLine': request.args.get('mainBusinessLine'),
        'registrationDateStart': request.args.get('registrationDateStart'),
        'registrationDateEnd': request.args.get('registrationDateEnd'),
        'postCode': request.args.get('postCode'),
        'businessIdRegistrationStart': request.args.get('businessIdRegistrationStart'),
        'businessIdRegistrationEnd': request.args.get('businessIdRegistrationEnd'),
        'page': request.args.get('page'),
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

@app.route('/output', methods=['GET'])
async def get_output():
    format_type = request.args.get('format')
    if format_type not in ["json", "csv"]:
        return jsonify({"error": "Invalid format. Use 'json' or 'csv'."}), 400

    # Generate output based on local_cache
    if format_type == "json":
        return jsonify(list(local_cache.values()))
    else:
        # Generate CSV output
        csv_data = "Business ID,Company Name,Trade Register Status,Last Modified\n"
        for company in local_cache.values():
            csv_data += f"{company['businessId']['value']},{company['names'][0]['name']},{company['tradeRegisterStatus']},{company['lastModified']}\n"
        return csv_data, 200, {'Content-Type': 'text/csv'}

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
# ```
# 
# ### Key Changes:
# 1. **Filtering Query Parameters**:
#    - Added a filtering step using dictionary comprehension to remove any parameters that have `None` values before passing them to the `fetch_company_data` function. This ensures that only valid parameters are included in the request.
# 
# ### Testing with `curl`
# 
# To test the `/companies` endpoint using `curl`, you can use the following command:
# 
# ```bash
# curl -X GET "http://localhost:8000/companies?name=Example%20Company&location=Helsinki"
# ```
# 
# In this example, you can adjust the parameters (`name`, `location`, etc.) based on the companies you wish to search for. The provided command demonstrates how to search for a company named "Example Company" located in Helsinki.
# 
# Let me know if you have any further questions or need additional assistance!