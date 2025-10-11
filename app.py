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
# def home():
#     """Dashboard page showing spend summary."""
#     summary = monthly_summary(DATABASE)
#     return render_template('index.html', summary=summary)

# @app.route('/dashboard')
def dashboard():
    """Unified dashboard with expenses + investments."""
    return render_template('dashboard.html')

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
@app.route('/get_summary')
def get_summary():
    month = request.args.get('month')
    year = request.args.get('year')

    query = 'SELECT category, SUM(amount) as total FROM expenses'
    filters = []
    params = []

    if month and year:
        filters.append('strftime("%m", date) = ? AND strftime("%Y", date) = ?')
        params += [f"{int(month):02d}", str(year)]
    elif year:
        filters.append('strftime("%Y", date) = ?')
        params.append(str(year))

    if filters:
        query += ' WHERE ' + ' AND '.join(filters)
    query += ' GROUP BY category'

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(query, params)
    data = cur.fetchall()
    conn.close()

    return jsonify([{'category': row['category'], 'total': row['total']} for row in data])

@app.route('/get_monthly_trend')
def get_monthly_trend():
    """Returns total spending grouped by month."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT SUBSTR(date, 1, 7) AS month, SUM(amount)
        FROM expenses
        GROUP BY month
        ORDER BY month
    """)
    data = cur.fetchall()
    conn.close()
    return jsonify([{'month': row['month'], 'total': row['SUM(amount)']} for row in data])

@app.route('/investments')
def investments():
    """Investment page UI."""
    return render_template('investments.html')

@app.route('/add_investment', methods=['POST'])
def add_investment():
    data = request.get_json() or request.form
    asset = data.get('asset')
    value = float(data.get('value', 0))
    date = data.get('date') or datetime.now().strftime('%Y-%m-%d')

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO investments (asset, value, date) VALUES (?, ?, ?)', (asset, value, date))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Investment added successfully!'})

@app.route('/get_investments')
def get_investments():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT asset, SUM(value) as total FROM investments GROUP BY asset')
    data = cur.fetchall()
    conn.close()
    return jsonify([{'asset': row['asset'], 'value': row['total']} for row in data])

@app.route('/get_investments_full')
def get_investments_full():
    month = request.args.get('month')
    year = request.args.get('year')

    query = 'SELECT * FROM investments'
    filters = []
    params = []

    if month and year:
        filters.append('strftime("%m", date) = ? AND strftime("%Y", date) = ?')
        params += [f"{int(month):02d}", str(year)]
    elif year:
        filters.append('strftime("%Y", date) = ?')
        params.append(str(year))

    if filters:
        query += ' WHERE ' + ' AND '.join(filters)
    query += ' ORDER BY date ASC'

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    return jsonify([
        {'id': row['id'], 'asset': row['asset'], 'value': row['value'], 'date': row['date']}
        for row in rows
    ])

@app.route('/update_investment/<int:investment_id>', methods=['POST'])
def update_investment(investment_id):
    data = request.get_json() or request.form
    asset = data.get('asset')
    value = float(data.get('value', 0))
    date = data.get('date') or datetime.now().strftime('%Y-%m-%d')

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        'UPDATE investments SET asset = ?, value = ?, date = ? WHERE id = ?',
        (asset, value, date, investment_id)
    )
    conn.commit()
    conn.close()
    return jsonify({'message': 'Investment updated successfully!'})


@app.route('/delete_investment/<int:investment_id>', methods=['DELETE'])
def delete_investment(investment_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM investments WHERE id = ?', (investment_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Investment deleted successfully!'})

if __name__ == '__main__':
    app.run(debug=True)
