Here is the final, well-formatted set of functional requirements for your accounting application:

### Functional Requirements

#### User Stories

1. **As an Employee**, I want to create an expense report so that I can submit my travel expenses for reimbursement.
2. **As an Employee**, I want to edit my expense report when it is in the 'draft' or 'rejected' state so that I can correct any mistakes before resubmitting.
3. **As an Employee**, I want to receive notifications when my report is rejected so that I can make the necessary corrections.
4. **As an Accountant**, I want to review submitted expense reports so that I can approve or reject them.
5. **As a Manager**, I want to receive notifications when an expense report is submitted so that I can review it promptly.
6. **As a Manager**, I want to approve or reject expense reports so that I can control the expenses incurred by my team.
7. **As an Accountant**, I want to create a payment once an expense report is approved by the manager so that the employee can be reimbursed.
8. **As a User**, I want to generate reports summarizing expenses by employee, department, or time period so that I can analyze spending.

#### Expense Report Workflow

- **States**: 
  - None > Draft > Submitted > Approved_by_Accounting > Approved_by_Manager > Pending_Payment > Processed
- **Editing**: Employees can edit expense reports only in 'draft' and 'rejected' states.

#### Payment Workflow

- **States**:
  - None > Created > Scheduled > Paid
- **Transition**: When a payment is marked as "paid," it triggers the transition of the associated expense report from "pending_payment" to "processed."

#### Expense Report Details

- **Fields**:
  - `employee_id`: String (identifier for the employee)
  - `destination`: String (travel destination)
  - `date`: String (format: DD.MM.YYYY)
  - `expenseList`: Array of objects containing:
    - `description`: Enum value from ["hotel", "taxi", "transportation", "meals", "other"]
    - `amount`: Decimal (two decimal precision, e.g., 99.99)
  - `amountPayable`: Decimal (total amount payable)

#### Notifications

- Manager is notified upon report submission.
- Accountant is notified upon manager approval.
- Employees are notified of rejections and required corrections.

#### Total Amount Calculation

- Calculate `totalAmount` after manager approval, summing all expenses except for 50% of the meals cost.

#### Reporting Features

- Ability to generate reports summarizing expenses by employee, department, time period, or other criteria.

#### API Endpoints

1. **Create Expense Report**
   - **Endpoint**: `POST /api/expense_reports`
   - **Request Body**: 
     ```json
     {
       "employee_id": "string",
       "destination": "string",
       "date": "DD.MM.YYYY",
       "expenseList": [
         {
           "description": "string",
           "amount": 99.99
         }
       ],
       "amountPayable": 99.99
     }
     ```
   - **Response**: 
     ```json
     {
       "id": "string",
       "status": "draft"
     }
     ```

