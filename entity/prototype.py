# To address the SSL certificate verification error that may arise when trying to connect to an external API, you can disable SSL verification in the aiohttp client session. However, please note that this is not recommended for production code due to security risks. Here's the modified `prototype.py` that includes a local cache and disables SSL verification:
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

# Constants for the Finnish Companies Registry API
COMPANIES_REGISTRY_API_URL = "https://api.prh.fi/companies"  # TODO: Update with the actual API URL

async def fetch_company_data(company_name):
    # Create an SSL context that does not verify certificates
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{COMPANIES_REGISTRY_API_URL}?name={company_name}", ssl=ssl_context) as response:
            if response.status == 200:
                return await response.json()
            else:
                return None

async def fetch_lei_data(company_name):
    # TODO: Replace with actual LEI data source
    return "LEI123456789"  # Placeholder for LEI; implement actual fetching logic

@app.route('/companies', methods=['GET'])
async def get_companies():
    name = request.args.get('name')
    if not name:
        return jsonify({"error": "Company name is required"}), 400

    # Fetch company data
    company_data = await fetch_company_data(name)
    if not company_data:
        return jsonify({"error": "No companies found"}), 404

    # Filter and enrich company data
    active_companies = []
    for company in company_data:
        if company.get('status') == 'Active':
            lei = await fetch_lei_data(company['company_name'])
            company['lei'] = lei if lei else "Not Available"
            active_companies.append(company)

            # Cache the company data locally
            local_cache[company['business_id']] = company

    return jsonify(active_companies)

@app.route('/output', methods=['GET'])
async def get_output():
    format_type = request.args.get('format')
    if format_type not in ["json", "csv"]:
        return jsonify({"error": "Invalid format. Use 'json' or 'csv'."}), 400

    # Generate output based on local_cache
    if format_type == "json":
        return jsonify(local_cache)
    else:
        # Generate CSV output
        csv_data = "Company Name,Business ID,Company Type,Registration Date,Status,LEI\n"
        for company in local_cache.values():
            csv_data += f"{company['company_name']},{company['business_id']},{company['company_type']},{company['registration_date']},{company['status']},{company['lei']}\n"
        return csv_data, 200, {'Content-Type': 'text/csv'}

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
# ```
# 
# ### Key Changes:
# 1. **SSL Certificate Verification**:
#    - The `fetch_company_data` function now creates an SSL context that disables hostname checking and certificate verification. This allows you to connect to the API without SSL errors.
# 
# 2. **Local Cache**:
#    - The fetched company data is stored in a local cache (`local_cache`) using the business ID as the key. This provides a way to simulate persistence.
# 
# 3. **CSV Generation**:
#    - The `/output` endpoint generates a CSV response based on the cached company data.
# 
# ### Important Note:
# Disabling SSL verification can expose your application to man-in-the-middle attacks. It is recommended to use this only for testing or prototyping purposes. In production, you should ensure that the API server has a valid SSL certificate and that your application can connect securely. 
# 
# Let me know if you need further adjustments or additional features!