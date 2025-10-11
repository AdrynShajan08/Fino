from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import sqlite3
from datetime import datetime
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from services.db_handler import create_tables, add_expense, get_summary_data
from services.analytics import monthly_summary


app = Flask(__name__)

#setup
DATABASE = 'data.db'
create_tables(DATABASE)

app.secret_key = 'test821'

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.before_request
def remove_trailing_slash():
    if request.path != '/' and request.path.endswith('/'):
        return redirect(request.path[:-1])



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                        (username, generate_password_hash(password)))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except:
            conn.close()
            return render_template('register.html', error="Username already exists")
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cur.fetchone()
        conn.close()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')
#     if request.method != 'POST':
#         return render_template('login.html')
# +    username = request.form['username']
# +    password = request.form['password']
# +    conn = get_db_connection()
# +    cur = conn.cursor()
# +    cur.execute("SELECT * FROM users WHERE username = ?", (username,))
# +    user = cur.fetchone()
# +    conn.close()
# +    if user and check_password_hash(user['password_hash'], password):
# +        session['user_id'] = user['id']
# +        session['username'] = user['username']
# +        return redirect(url_for('dashboard'))
# +    return render_template('login.html', error="Invalid credentials")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch totals
    cur.execute("SELECT SUM(amount) as total_expenses FROM expenses WHERE user_id = ?", (user_id,))
    total_expenses = cur.fetchone()['total_expenses'] or 0

    cur.execute("SELECT SUM(value) as total_investments FROM investments WHERE user_id = ?", (user_id,))
    total_investments = cur.fetchone()['total_investments'] or 0

    message = None
    error = None

    # Handle password update
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cur.fetchone()

        if not check_password_hash(user['password_hash'], current_password):
            error = "❌ Current password is incorrect."
        elif new_password != confirm_password:
            error = "❌ New passwords do not match."
        else:
            cur.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                        (generate_password_hash(new_password), user_id))
            conn.commit()
            message = "✅ Password updated successfully!"

    conn.close()
    return render_template('profile.html',
                           username=session['username'],
                           total_expenses=total_expenses,
                           total_investments=total_investments,
                           message=message,
                           error=error)


#routes
@app.route('/')
# @app.route('/dashboard')
@login_required
def dashboard():
    """Unified dashboard with expenses + investments."""
    return render_template('dashboard.html', username=session['username'])


@app.route('/add_expense', methods=['GET', 'POST'])
@login_required
def add_expense_route():
    """Add a new expense (form or voice)."""
    if request.method == 'POST':
        data = request.get_json() or request.form
        user_id = session['user_id']
        amount = float(data.get('amount', 0))
        category = data.get('category', 'other').lower()
        description = data.get('description', '')
        date = data.get('date') or datetime.now().strftime('%Y-%m-%d')

        add_expense(DATABASE, user_id, category, amount, date, description)
        return jsonify({'message': 'Expense added successfully!'})
    return render_template('add_expense.html')

@app.route('/get_summary', methods=['GET'])
@app.route('/get_summary')
@login_required
def get_summary():
    month = request.args.get('month')
    year = request.args.get('year')

    user_id=session['user_id']
    query = 'SELECT category, SUM(amount) as total FROM expenses WHERE user_id = ?'
    filters = []
    params = [user_id]

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
@login_required
def get_monthly_trend():
    """Returns total spending grouped by month."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT SUBSTR(date, 1, 7) AS month, SUM(amount)
        FROM expenses
        WHERE
        GROUP BY month
        ORDER BY month
    """)
    data = cur.fetchall()
    conn.close()
    return jsonify([{'month': row['month'], 'total': row['SUM(amount)']} for row in data])

@app.route('/investments')
@login_required
def investments():
    """Investment page UI."""
    return render_template('investments.html')

@app.route('/add_investment', methods=['POST'])
@login_required
def add_investment():
    data = request.get_json() or request.form
    user_id = session['user_id']
    asset = data.get('asset')
    value = float(data.get('value', 0))
    date = data.get('date') or datetime.now().strftime('%Y-%m-%d')

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO investments (user_id, asset, value, date) VALUES (?, ?, ?, ?)', (user_id, asset, value, date))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Investment added successfully!'})

@app.route('/get_investments')
@login_required
def get_investments():
    conn = get_db_connection()
    cur = conn.cursor()
    user_id = session['user_id']
    cur.execute('SELECT asset, SUM(value) as total FROM investments GROUP BY asset WHERE user_id = ?')
    params = [user_id]
    data = cur.fetchall()
    conn.close()
    return jsonify([{'asset': row['asset'], 'value': row['total']} for row in data])

@app.route('/get_investments_full')
@login_required
def get_investments_full():
    month = request.args.get('month')
    year = request.args.get('year')

    user_id = session['user_id']
    query = 'SELECT * FROM investments WHERE user_id = ?'
    filters = []
    params = [user_id]

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
@login_required
def update_investment(investment_id):
    data = request.get_json() or request.form
    asset = data.get('asset')
    value = float(data.get('value', 0))
    date = data.get('date') or datetime.now().strftime('%Y-%m-%d')

    conn = get_db_connection()
    cur = conn.cursor()

    user_id = session['user_id']
    cur.execute(
        'UPDATE investments SET user_id = ?, asset = ?, value = ?, date = ? WHERE id = ?',
        (user_id, asset, value, date, investment_id)
    )
    conn.commit()
    conn.close()
    return jsonify({'message': 'Investment updated successfully!'})


@app.route('/delete_investment/<int:investment_id>', methods=['DELETE'])
@login_required
def delete_investment(investment_id):
    conn = get_db_connection()
    cur = conn.cursor()
    user_id = session['user_id']
    cur.execute('DELETE FROM investments WHERE user_id = ?, id = ?', (user_id, investment_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Investment deleted successfully!'})



if __name__ == '__main__':
    # print(app.url_map)
    app.run(debug=True)
