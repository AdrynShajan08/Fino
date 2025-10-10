from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime
from services.db_handler import create_tables, add_expense, get_summary_data
from services.analytics import monthly_summary

app = Flask(__name__)

#setup
DATABASE = 'data.db'
create_tables(DATABASE)

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

#routes
@app.route('/')
def home():
    """Dashboard page showing spend summary."""
    summary = monthly_summary(DATABASE)
    return render_template('index.html', summary=summary)

@app.route('/add_expense', methods=['GET', 'POST'])
def add_expense_route():
    """Add a new expense (form or voice)."""
    if request.method == 'POST':
        data = request.get_json() or request.form
        amount = float(data.get('amount', 0))
        category = data.get('category', 'other').lower()
        description = data.get('description', '')
        date = data.get('date') or datetime.now().strftime('%Y-%m-%d')

        add_expense(DATABASE, date, category, amount, description)
        return jsonify({'message': 'Expense added successfully!'})
    return render_template('add_expense.html')

@app.route('/get_summary', methods=['GET'])
def get_summary():
    """Return spend data as JSON (for charts)."""
    summary_data = get_summary_data(DATABASE)
    return jsonify(summary_data)

@app.route('/investments')
def investments():
    """Investment page placeholder."""
    return render_template('investments.html')


if __name__ == '__main__':
    app.run(debug=True)
