# Here's a basic implementation of the `prototype.py` file using Quart and aiohttp, incorporating the requirements you've provided. This prototype will be a simple representation of the API endpoints without full error handling or validation, using mocks and placeholders where necessary.
# 
# ```python
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request
from datetime import datetime
import aiohttp

app = Quart(__name__)
QuartSchema(app)

# In-memory storage for expense reports and payments
expense_reports = {}
payments = {}
current_expense_id = 1
current_payment_id = 1

# Utility function to calculate total amount payable
def calculate_total_amount(expense_list):
    total = 0.0
    for expense in expense_list:
        if expense['description'] == 'meals':
            total += expense['amount'] * 0.5  # Only 50% of meals cost is included
        else:
            total += expense['amount']
    return round(total, 2)

@app.route('/api/expense_reports', methods=['POST'])
async def create_expense_report():
    global current_expense_id
    data = await request.get_json()
    
    # Calculate amount payable
    data['amountPayable'] = calculate_total_amount(data['expenseList'])
    data['status'] = 'draft'
    expense_reports[current_expense_id] = data
    expense_reports[current_expense_id]['id'] = current_expense_id
    current_expense_id += 1
    return jsonify(expense_reports[current_expense_id - 1]), 201

@app.route('/api/expense_reports/<int:expense_id>', methods=['PUT'])
async def edit_expense_report(expense_id):
    if expense_id not in expense_reports:
        return jsonify({'error': 'Expense report not found'}), 404

    data = await request.get_json()
    
    # Allow editing only in 'draft' or 'rejected' state
    if expense_reports[expense_id]['status'] not in ['draft', 'rejected']:
        return jsonify({'error': 'Cannot edit report in current state'}), 403
    
    # Update report and recalculate amount
    expense_reports[expense_id].update(data)
    expense_reports[expense_id]['amountPayable'] = calculate_total_amount(data['expenseList'])
    return jsonify(expense_reports[expense_id]), 200

@app.route('/api/expense_reports/<int:expense_id>/submit', methods=['POST'])
async def submit_expense_report(expense_id):
    if expense_id not in expense_reports:
        return jsonify({'error': 'Expense report not found'}), 404
    
    expense_reports[expense_id]['status'] = 'submitted'
    # TODO: Trigger notification to manager (not implemented in this prototype)
    return jsonify({'status': 'submitted'}), 200

@app.route('/api/expense_reports/<int:expense_id>/approve', methods=['POST'])
async def approve_expense_report(expense_id):
    if expense_id not in expense_reports:
        return jsonify({'error': 'Expense report not found'}), 404
    
    expense_reports[expense_id]['status'] = 'approved_by_manager'
    # TODO: Trigger notification to accountant (not implemented in this prototype)
    return jsonify({'status': 'approved_by_manager'}), 200

@app.route('/api/payments', methods=['POST'])
async def create_payment():
    global current_payment_id
    data = await request.get_json()

    # TODO: Validate the expense_report_id exists and is in 'approved_by_manager' state (not implemented)
    payment = {
        'id': current_payment_id,
        'expense_report_id': data['expense_report_id'],
        'amount_payable': data['amount_payable'],
        'status': 'created'
    }
    payments[current_payment_id] = payment
    current_payment_id += 1
    return jsonify(payment), 201

# Entry point
if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
# ```
# 
# ### Key Points
# - The prototype implements the basic structure and endpoints for creating, editing, submitting, approving expense reports, and creating payments.
# - The `calculate_total_amount` function calculates the total amount payable according to the specified rules.
# - The code includes placeholders (denoted by TODO comments) for notifications and validation checks that are not fully implemented in this prototype.
# - The in-memory storage (`expense_reports` and `payments`) is used for simplicity; in a complete implementation, you would likely use a database.
# 
# Feel free to adjust the implementation details as needed, and you can further expand on the TODOs based on your specific requirements and integration needs.