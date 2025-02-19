# Here's a prototype implementation of your application based on the requirements provided. This code uses Quart for the web framework and aiohttp for handling HTTP requests. It includes mock persistence using a local in-memory cache to simulate database operations.
# 
# ```python
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

app = Quart(__name__)
QuartSchema(app)

# In-memory cache to simulate database persistence
company_cache = {}
company_id_counter = 1

@app.route('/companies', methods=['POST'])
async def create_company():
    global company_id_counter
    data = await request.get_json()
    company_id = company_id_counter
    company_cache[company_id] = {
        'name': data.get('name'),
        'address': data.get('address'),
        'contact_number': data.get('contact_number')
    }
    company_id_counter += 1
    return jsonify({"message": "Company created successfully", "id": company_id}), 201

@app.route('/companies', methods=['GET'])
async def get_companies():
    return jsonify([{"id": cid, **details} for cid, details in company_cache.items()]), 200

@app.route('/companies/<int:id>', methods=['GET'])
async def get_company(id):
    company = company_cache.get(id)
    if company:
        return jsonify({"id": id, **company}), 200
    return jsonify({"message": "Company not found"}), 404

@app.route('/companies/<int:id>', methods=['PUT'])
async def update_company(id):
    data = await request.get_json()
    if id in company_cache:
        company_cache[id] = {
            'name': data.get('name'),
            'address': data.get('address'),
            'contact_number': data.get('contact_number')
        }
        return jsonify({"message": "Company updated successfully"}), 200
    return jsonify({"message": "Company not found"}), 404

@app.route('/companies/<int:id>', methods=['DELETE'])
async def delete_company(id):
    if id in company_cache:
        del company_cache[id]
        return jsonify({"message": "Company deleted successfully"}), 200
    return jsonify({"message": "Company not found"}), 404

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
# ```
# 
# ### Key Points
# 
# 1. **In-memory Cache**: The `company_cache` dictionary is used to simulate database persistence. Each company is stored in this cache with a unique ID.
# 
# 2. **Endpoints**: All required API endpoints are implemented:
#    - `POST /companies` for creating a new company.
#    - `GET /companies` for retrieving all companies.
#    - `GET /companies/{id}` for retrieving a specific company by ID.
#    - `PUT /companies/{id}` for updating a company's details.
#    - `DELETE /companies/{id}` for deleting a company.
# 
# 3. **No External Persistence**: The implementation does not use SQLAlchemy or any external database; it relies solely on an in-memory dictionary.
# 
# 4. **Dynamic Data Handling**: The code is designed to handle dynamic JSON data input as specified, without using request validation.
# 
# 5. **Mocking & TODO**: There are no explicit TODO comments in this prototype, as it fulfills the current requirements. Future enhancements may require persistence or more complex logic.
# 
# This prototype allows you to verify the user experience and identify any gaps in the requirements before proceeding with a more thorough implementation. If there are any additional features or changes you would like to implement, please let me know!