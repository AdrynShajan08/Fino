from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import sqlite3
from datetime import datetime
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from services.db_handler import create_tables, get_summary_data
from services.analytics import monthly_summary
import os
from contextlib import contextmanager

app = Flask(__name__)

# Configuration
DATABASE = 'data.db'
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

# Initialize database
create_tables(DATABASE)


# Context manager for database connections
@contextmanager
def get_db_connection():
    """Context manager for database connections with automatic cleanup."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def login_required(f):
    """Decorator to require login for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def validate_numeric(value, field_name="value"):
    """Validate and convert numeric input."""
    try:
        num = float(value)
        if num < 0:
            raise ValueError(f"{field_name} must be positive")
        return num
    except (ValueError, TypeError):
        raise ValueError(f"Invalid {field_name}")


def validate_date(date_str):
    """Validate date format."""
    if not date_str:
        return datetime.now().strftime('%Y-%m-%d')
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return date_str
    except ValueError:
        raise ValueError("Invalid date format. Use YYYY-MM-DD")


@app.before_request
def remove_trailing_slash():
    """Remove trailing slashes from URLs."""
    if request.path != '/' and request.path.endswith('/'):
        return redirect(request.path[:-1])


# Authentication Routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            return render_template('register.html', error="Username and password are required")
        
        if len(password) < 8:
            return render_template('register.html', error="Password must be at least 8 characters")
        
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                           (username, generate_password_hash(password)))
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return render_template('register.html', error="Username already exists")
        except Exception as e:
            app.logger.error(f"Registration error: {e}")
            return render_template('register.html', error="Registration failed")
    
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            return render_template('login.html', error="Username and password are required")
        
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM users WHERE username = ?", (username,))
                user = cur.fetchone()
            
            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                return redirect(url_for('dashboard'))
            
            return render_template('login.html', error="Invalid credentials")
        except Exception as e:
            app.logger.error(f"Login error: {e}")
            return render_template('login.html', error="Login failed")
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    """User logout."""
    session.clear()
    return redirect(url_for('login'))


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page with password update."""
    user_id = session['user_id']
    message = None
    error = None
    
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            # Fetch totals
            cur.execute("SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE user_id = ?", 
                       (user_id,))
            total_expenses = cur.fetchone()['total']
            
            cur.execute("SELECT COALESCE(SUM(value), 0) as total FROM investments WHERE user_id = ?", 
                       (user_id,))
            total_investments = cur.fetchone()['total']
            
            # Handle password update
            if request.method == 'POST':
                current_password = request.form.get('current_password', '')
                new_password = request.form.get('new_password', '')
                confirm_password = request.form.get('confirm_password', '')
                
                cur.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,))
                user = cur.fetchone()
                
                if not check_password_hash(user['password_hash'], current_password):
                    error = "Current password is incorrect."
                elif len(new_password) < 8:
                    error = "New password must be at least 8 characters."
                elif new_password != confirm_password:
                    error = "New passwords do not match."
                else:
                    cur.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                               (generate_password_hash(new_password), user_id))
                    message = "Password updated successfully!"
        
        return render_template('profile.html',
                             username=session['username'],
                             total_expenses=total_expenses,
                             total_investments=total_investments,
                             message=message,
                             error=error)
    except Exception as e:
        app.logger.error(f"Profile error: {e}")
        return render_template('profile.html', error="Error loading profile")


# Dashboard Routes
@app.route('/')
@login_required
def dashboard():
    """Unified dashboard with expenses and investments."""
    return render_template('dashboard.html', username=session['username'])


# Expense Routes
@app.route('/add_expense', methods=['GET'])
@login_required
def add_expense_page():
    """Expense page UI."""
    return render_template('add_expense.html')


@app.route('/add_expense', methods=['POST'])
@login_required
def add_expense():
    """Add a new expense."""
    try:
        data = request.get_json() or request.form
        user_id = session['user_id']
        
        category = data.get('category', '').strip()
        if not category:
            return jsonify({'error': 'Category is required'}), 400
        
        amount = validate_numeric(data.get('amount'), 'Amount')
        date = validate_date(data.get('date'))
        description = data.get('description', '').strip()
        
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                'INSERT INTO expenses (user_id, category, amount, date, description) VALUES (?, ?, ?, ?, ?)',
                (user_id, category, amount, date, description)
            )
        
        return jsonify({'message': 'Expense added successfully!'})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        app.logger.error(f"Add expense error: {e}")
        return jsonify({'error': 'Failed to add expense'}), 500


@app.route('/get_expenses')
@login_required
def get_expenses():
    """Get expenses grouped by category."""
    try:
        user_id = session['user_id']
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                'SELECT category, SUM(amount) as total FROM expenses WHERE user_id = ? GROUP BY category',
                (user_id,)
            )
            data = cur.fetchall()
        
        return jsonify([{'category': row['category'], 'total': row['total']} for row in data])
    except Exception as e:
        app.logger.error(f"Get expenses error: {e}")
        return jsonify({'error': 'Failed to fetch expenses'}), 500


@app.route('/get_expenses_full')
@login_required
def get_expenses_full():
    """Get all expenses with optional month/year filtering."""
    try:
        user_id = session['user_id']
        month = request.args.get('month')
        year = request.args.get('year')
        
        query = 'SELECT * FROM expenses WHERE user_id = ?'
        params = [user_id]
        
        if month and year:
            query += ' AND strftime("%m", date) = ? AND strftime("%Y", date) = ?'
            params.extend([f"{int(month):02d}", str(year)])
        elif year:
            query += ' AND strftime("%Y", date) = ?'
            params.append(str(year))
        
        query += ' ORDER BY date DESC'
        
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            rows = cur.fetchall()
        
        return jsonify([
            {
                'id': row['id'],
                'category': row['category'],
                'amount': row['amount'],
                'date': row['date'],
                'description': row['description']
            }
            for row in rows
        ])
    except Exception as e:
        app.logger.error(f"Get expenses full error: {e}")
        return jsonify({'error': 'Failed to fetch expenses'}), 500


@app.route('/update_expense/<int:expense_id>', methods=['POST'])
@login_required
def update_expense(expense_id):
    """Update an existing expense."""
    try:
        data = request.get_json() or request.form
        user_id = session['user_id']
        
        category = data.get('category', '').strip()
        if not category:
            return jsonify({'error': 'Category is required'}), 400
        
        amount = validate_numeric(data.get('amount'), 'Amount')
        date = validate_date(data.get('date'))
        description = data.get('description', '').strip()
        
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                'UPDATE expenses SET category = ?, amount = ?, date = ?, description = ? WHERE id = ? AND user_id = ?',
                (category, amount, date, description, expense_id, user_id)
            )
            
            if cur.rowcount == 0:
                return jsonify({'error': 'Expense not found or unauthorized'}), 404
        
        return jsonify({'message': 'Expense updated successfully!'})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        app.logger.error(f"Update expense error: {e}")
        return jsonify({'error': 'Failed to update expense'}), 500


@app.route('/delete_expense/<int:expense_id>', methods=['DELETE'])
@login_required
def delete_expense(expense_id):
    """Delete an expense."""
    try:
        user_id = session['user_id']
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute('DELETE FROM expenses WHERE id = ? AND user_id = ?', (expense_id, user_id))
            
            if cur.rowcount == 0:
                return jsonify({'error': 'Expense not found or unauthorized'}), 404
        
        return jsonify({'message': 'Expense deleted successfully!'})
    except Exception as e:
        app.logger.error(f"Delete expense error: {e}")
        return jsonify({'error': 'Failed to delete expense'}), 500


@app.route('/get_summary')
@login_required
def get_summary():
    """Get expense summary grouped by category with optional filtering."""
    try:
        user_id = session['user_id']
        month = request.args.get('month')
        year = request.args.get('year')
        
        query = 'SELECT category, SUM(amount) as total FROM expenses WHERE user_id = ?'
        params = [user_id]
        
        if month and year:
            query += ' AND strftime("%m", date) = ? AND strftime("%Y", date) = ?'
            params.extend([f"{int(month):02d}", str(year)])
        elif year:
            query += ' AND strftime("%Y", date) = ?'
            params.append(str(year))
        
        query += ' GROUP BY category'
        
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            rows = cur.fetchall()
        
        labels = [row['category'] for row in rows]
        values = [row['total'] for row in rows]
        
        return jsonify({'labels': labels, 'values': values})
    except Exception as e:
        app.logger.error(f"Get summary error: {e}")
        return jsonify({'error': 'Failed to fetch summary'}), 500


@app.route('/get_monthly_trend')
@login_required
def get_monthly_trend():
    """Returns total spending grouped by month."""
    try:
        user_id = session['user_id']
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT strftime('%Y-%m', date) AS month, SUM(amount) as total
                FROM expenses
                WHERE user_id = ?
                GROUP BY month
                ORDER BY month
            """, (user_id,))
            data = cur.fetchall()
        
        return jsonify([{'month': row['month'], 'total': row['total']} for row in data])
    except Exception as e:
        app.logger.error(f"Get monthly trend error: {e}")
        return jsonify({'error': 'Failed to fetch monthly trend'}), 500


# Investment Routes
@app.route('/investments')
@login_required
def investments():
    """Investment page UI."""
    return render_template('investments.html')


@app.route('/add_investment', methods=['POST'])
@login_required
def add_investment():
    """Add a new investment."""
    try:
        data = request.get_json() or request.form
        user_id = session['user_id']
        
        asset = data.get('asset', '').strip()
        if not asset:
            return jsonify({'error': 'Asset is required'}), 400
        
        value = validate_numeric(data.get('value'), 'Value')
        date = validate_date(data.get('date'))
        
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                'INSERT INTO investments (user_id, asset, value, date) VALUES (?, ?, ?, ?)',
                (user_id, asset, value, date)
            )
        
        return jsonify({'message': 'Investment added successfully!'})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        app.logger.error(f"Add investment error: {e}")
        return jsonify({'error': 'Failed to add investment'}), 500


@app.route('/get_investments')
@login_required
def get_investments():
    """Get investments grouped by asset."""
    try:
        user_id = session['user_id']
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                'SELECT asset, SUM(value) as total FROM investments WHERE user_id = ? GROUP BY asset',
                (user_id,)
            )
            data = cur.fetchall()
        
        return jsonify([{'asset': row['asset'], 'value': row['total']} for row in data])
    except Exception as e:
        app.logger.error(f"Get investments error: {e}")
        return jsonify({'error': 'Failed to fetch investments'}), 500


@app.route('/get_investments_full')
@login_required
def get_investments_full():
    """Get all investments with optional month/year filtering."""
    try:
        user_id = session['user_id']
        month = request.args.get('month')
        year = request.args.get('year')
        
        query = 'SELECT * FROM investments WHERE user_id = ?'
        params = [user_id]
        
        if month and year:
            query += ' AND strftime("%m", date) = ? AND strftime("%Y", date) = ?'
            params.extend([f"{int(month):02d}", str(year)])
        elif year:
            query += ' AND strftime("%Y", date) = ?'
            params.append(str(year))
        
        query += ' ORDER BY date DESC'
        
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            rows = cur.fetchall()
        
        return jsonify([
            {
                'id': row['id'],
                'asset': row['asset'],
                'value': row['value'],
                'date': row['date']
            }
            for row in rows
        ])
    except Exception as e:
        app.logger.error(f"Get investments full error: {e}")
        return jsonify({'error': 'Failed to fetch investments'}), 500


@app.route('/update_investment/<int:investment_id>', methods=['POST'])
@login_required
def update_investment(investment_id):
    """Update an existing investment."""
    try:
        data = request.get_json() or request.form
        user_id = session['user_id']
        
        asset = data.get('asset', '').strip()
        if not asset:
            return jsonify({'error': 'Asset is required'}), 400
        
        value = validate_numeric(data.get('value'), 'Value')
        date = validate_date(data.get('date'))
        
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                'UPDATE investments SET asset = ?, value = ?, date = ? WHERE id = ? AND user_id = ?',
                (asset, value, date, investment_id, user_id)
            )
            
            if cur.rowcount == 0:
                return jsonify({'error': 'Investment not found or unauthorized'}), 404
        
        return jsonify({'message': 'Investment updated successfully!'})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        app.logger.error(f"Update investment error: {e}")
        return jsonify({'error': 'Failed to update investment'}), 500


@app.route('/delete_investment/<int:investment_id>', methods=['DELETE'])
@login_required
def delete_investment(investment_id):
    """Delete an investment."""
    try:
        user_id = session['user_id']
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute('DELETE FROM investments WHERE id = ? AND user_id = ?', (investment_id, user_id))
            
            if cur.rowcount == 0:
                return jsonify({'error': 'Investment not found or unauthorized'}), 404
        
        return jsonify({'message': 'Investment deleted successfully!'})
    except Exception as e:
        app.logger.error(f"Delete investment error: {e}")
        return jsonify({'error': 'Failed to delete investment'}), 500


@app.route('/get_investment_trend')
@login_required
def get_investment_trend():
    """Get investment trend over time."""
    try:
        user_id = session['user_id']
        period = request.args.get('period', 'month')
        
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            if period == 'year':
                cur.execute("""
                    SELECT strftime('%Y', date) as period, SUM(value) as total_value
                    FROM investments
                    WHERE user_id = ?
                    GROUP BY strftime('%Y', date)
                    ORDER BY period
                """, (user_id,))
            else:
                cur.execute("""
                    SELECT strftime('%Y-%m', date) as period, SUM(value) as total_value
                    FROM investments
                    WHERE user_id = ?
                    GROUP BY strftime('%Y-%m', date)
                    ORDER BY period
                """, (user_id,))
            
            data = cur.fetchall()
        
        labels = [row['period'] for row in data]
        values = [row['total_value'] for row in data]
        
        return jsonify({'labels': labels, 'values': values})
    except Exception as e:
        app.logger.error(f"Get investment trend error: {e}")
        return jsonify({'error': 'Failed to fetch investment trend'}), 500


if __name__ == '__main__':
    app.run(debug=True)