from quart import Quart, request, jsonify
from quart_schema import QuartSchema
import aiohttp
import ssl
from app_init.app_init import entity_service

app = Quart(__name__)
QuartSchema(app)
COMPANIES_REGISTRY_API_URL = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"

async def fetch_company_data(query_params):
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
        'page': request_data.get('page')
    }
    filtered_params = {k: v for k, v in query_params.items() if v is not None}
    company_data = await fetch_company_data(filtered_params)
    if not company_data or 'companies' not in company_data:
        return jsonify({"error": "No companies found"}), 404
    for company in company_data['companies']:
        entity_service.add_item(token=token, entity_model="companies", entity_version=ENTITY_VERSION, entity=company)
    return jsonify(company_data)

@app.route('/output', methods=['POST'])
async def get_output():
    request_data = await request.get_json()
    format_type = request_data.get('format')
    if format_type not in ["json", "csv"]:
        return jsonify({"error": "Invalid format. Use 'json' or 'csv'."}), 400
    companies = entity_service.get_items(token=token, entity_model="companies", entity_version=ENTITY_VERSION)
    if format_type == "json":
        return jsonify(companies)
    else:
        csv_data = "Business ID,Company Name,Trade Register Status,Last Modified\n"
        for company in companies:
            business_id = company.get('businessId', {}).get('value', 'N/A')
            company_name = company.get('names', [{}])[0].get('name', 'N/A')
            trade_register_status = company.get('tradeRegisterStatus', 'N/A')
            last_modified = company.get('lastModified', 'N/A')
            csv_data += f"{business_id},{company_name},{trade_register_status},{last_modified}\n"
        return csv_data, 200, {'Content-Type': 'text/csv'}

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)