# The prototype provided earlier simulates a backend application using an in-memory cache to store company details. However, it does not connect to a PostgreSQL database, as per your request for a working prototype without using SQLAlchemy or any external persistence mechanism.
# 
# If you want to store the company details in a PostgreSQL database, you would need to include a proper database connection and use an ORM like SQLAlchemy or a direct database connection approach with psycopg2 or asyncpg. However, since you specified that we should not use any external implementation for persistence or cache, the prototype will continue to use local cache.
# 
# Here’s the updated working prototype `prototype.py` code, ensuring clarity on its limitations regarding PostgreSQL storage:
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
# ### Explanation
# 
# 1. **In-memory Cache**: The `company_cache` dictionary is used to store company details locally. This means the data will not persist beyond the application's runtime.
# 
# 2. **No Database Interaction**: There is no connection to a PostgreSQL database in this prototype. Hence, the application will not store the company details in a PostgreSQL database.
# 
# 3. **Functionality**: All required API endpoints are implemented, allowing you to create, retrieve, update, and delete company details.
# 
# 4. **Testing & Validation**: You can test the endpoints using tools like Postman or cURL to verify the application's functionality.
# 
# If your goal is to eventually store data in a PostgreSQL database, you would need to implement database connectivity and persistence in a later version of the application. If you have any specific requirements or additional features you want to discuss, feel free to let me know!