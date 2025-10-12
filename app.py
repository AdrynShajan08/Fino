"""
Optimized Fino Flask Application
"""
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from datetime import datetime
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import os
import logging
from logging.handlers import RotatingFileHandler

# Import configuration
from config import config

# Import services
from services.db_handler import initialize_database
from services.expense_service import ExpenseService
from services.investment_service import InvestmentService

# Import utilities
from utils.validators import (
    validate_numeric, validate_date, validate_month_year,
    validate_string, error_response, success_response
)
from utils.cache import SimpleCache
from utils.rate_limiter import rate_limit

# Initialize Flask app
app = Flask(__name__)

# Load configuration
env = os.environ.get('FLASK_ENV', 'development')
app.config.from_object(config[env])

DATABASE = app.config['DATABASE']

# Initialize database
initialize_database(DATABASE)

# Initialize services
expense_service = ExpenseService(DATABASE)
investment_service = InvestmentService(DATABASE)

# Initialize cache
cache = SimpleCache(ttl_seconds=app.config['CACHE_TTL'])

# Setup logging
def setup_logging(app):
    """Configure application logging."""
    if not app.debug:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            'logs/fino.log',
            maxBytes=10485760,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('Fino startup')

setup_logging(app)

# Decorators
def login_required(f):
    """Decorator to require login for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

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
        try:
            username = validate_string(
                request.form.get('username', '').strip(),
                'Username',
                min_length=3,
                max_length=50
            )
            password = request.form.get('password', '')
            
            if len(password) < 8:
                return render_template('register.html', 
                    error="Password must be at least 8 characters")
            
            # Use expense_service connection (any service will do)
            with expense_service.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, generate_password_hash(password))
                )
            
            app.logger.info(f"New user registered: {username}")
            return redirect(url_for('login'))
            
        except ValueError as e:
            return render_template('register.html', error=str(e))
        except Exception as e:
            if 'UNIQUE constraint failed' in str(e):
                return render_template('register.html', 
                    error="Username already exists")
            app.logger.error(f"Registration error: {e}")
            return render_template('register.html', 
                error="Registration failed")
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login."""
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            
            if not username or not password:
                return render_template('login.html', 
                    error="Username and password are required")
            
            with expense_service.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM users WHERE username = ?", (username,))
                user = cur.fetchone()
            
            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                app.logger.info(f"User logged in: {username}")
                return redirect(url_for('dashboard'))
            
            return render_template('login.html', error="Invalid credentials")
            
        except Exception as e:
            app.logger.error(f"Login error: {e}")
            return render_template('login.html', error="Login failed")
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """User logout."""
    username = session.get('username')
    session.clear()
    if username:
        app.logger.info(f"User logged out: {username}")
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page with password update."""
    user_id = session['user_id']
    message = None
    error = None
    
    try:
        # Get totals
        total_expenses = expense_service.get_total_expenses(user_id)
        total_investments = investment_service.get_total_investments(user_id)
        
        # Handle password update
        if request.method == 'POST':
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            with expense_service.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT password_hash FROM users WHERE id = ?", 
                    (user_id,)
                )
                user = cur.fetchone()
                
                if not check_password_hash(user['password_hash'], current_password):
                    error = "Current password is incorrect."
                elif len(new_password) < 8:
                    error = "New password must be at least 8 characters."
                elif new_password != confirm_password:
                    error = "New passwords do not match."
                else:
                    cur.execute(
                        "UPDATE users SET password_hash = ? WHERE id = ?",
                        (generate_password_hash(new_password), user_id)
                    )
                    message = "Password updated successfully!"
                    app.logger.info(f"Password updated for user_id: {user_id}")
        
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
@rate_limit(max_requests=30, window_seconds=60)
def add_expense():
    """Add a new expense."""
    try:
        data = request.get_json() or request.form
        user_id = session['user_id']
        
        # Validate inputs
        category = validate_string(data.get('category', ''), 'Category')
        amount = validate_numeric(data.get('amount'), 'Amount')
        date = validate_date(data.get('date'))
        description = data.get('description', '').strip()
        
        # Add expense
        expense_id = expense_service.add_expense(
            user_id, category, amount, date, description
        )
        
        # Invalidate cache
        cache.invalidate(f"user_{user_id}")
        
        app.logger.info(f"Expense added: {expense_id} for user {user_id}")
        return success_response('Expense added successfully!', {'id': expense_id})
        
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        app.logger.error(f"Add expense error: {e}")
        return error_response('Failed to add expense', 500)

@app.route('/get_expenses')
@login_required
def get_expenses():
    """Get expenses grouped by category."""
    try:
        user_id = session['user_id']
        cache_key = f"user_{user_id}_expenses_summary"
        
        # Check cache
        cached = cache.get(cache_key)
        if cached:
            return jsonify(cached)
        
        # Get summary
        summary = expense_service.get_summary(user_id)
        data = [
            {'category': label, 'total': value}
            for label, value in zip(summary['labels'], summary['values'])
        ]
        
        # Cache result
        cache.set(cache_key, data)
        
        return jsonify(data)
        
    except Exception as e:
        app.logger.error(f"Get expenses error: {e}")
        return error_response('Failed to fetch expenses', 500)

@app.route('/get_expenses_full')
@login_required
def get_expenses_full():
    """Get all expenses with optional month/year filtering."""
    try:
        user_id = session['user_id']
        month = request.args.get('month')
        year = request.args.get('year')
        
        # Validate filters
        if month or year:
            month, year = validate_month_year(month, year)
        
        # Get expenses
        expenses = expense_service.get_expenses(user_id, month, year)
        
        return jsonify(expenses)
        
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        app.logger.error(f"Get expenses full error: {e}")
        return error_response('Failed to fetch expenses', 500)

@app.route('/update_expense/<int:expense_id>', methods=['POST'])
@login_required
@rate_limit(max_requests=30, window_seconds=60)
def update_expense(expense_id):
    """Update an existing expense."""
    try:
        data = request.get_json() or request.form
        user_id = session['user_id']
        
        # Validate inputs
        category = validate_string(data.get('category', ''), 'Category')
        amount = validate_numeric(data.get('amount'), 'Amount')
        date = validate_date(data.get('date'))
        description = data.get('description', '').strip()
        
        # Update expense
        success = expense_service.update_expense(
            expense_id, user_id, category, amount, date, description
        )
        
        if not success:
            return error_response('Expense not found or unauthorized', 404)
        
        # Invalidate cache
        cache.invalidate(f"user_{user_id}")
        
        app.logger.info(f"Expense updated: {expense_id} for user {user_id}")
        return success_response('Expense updated successfully!')
        
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        app.logger.error(f"Update expense error: {e}")
        return error_response('Failed to update expense', 500)

@app.route('/delete_expense/<int:expense_id>', methods=['DELETE'])
@login_required
@rate_limit(max_requests=30, window_seconds=60)
def delete_expense(expense_id):
    """Delete an expense."""
    try:
        user_id = session['user_id']
        
        success = expense_service.delete_expense(expense_id, user_id)
        
        if not success:
            return error_response('Expense not found or unauthorized', 404)
        
        # Invalidate cache
        cache.invalidate(f"user_{user_id}")
        
        app.logger.info(f"Expense deleted: {expense_id} for user {user_id}")
        return success_response('Expense deleted successfully!')
        
    except Exception as e:
        app.logger.error(f"Delete expense error: {e}")
        return error_response('Failed to delete expense', 500)

@app.route('/get_summary')
@login_required
def get_summary():
    """Get expense summary grouped by category with optional filtering."""
    try:
        user_id = session['user_id']
        month = request.args.get('month')
        year = request.args.get('year')
        
        # Validate filters
        if month or year:
            month, year = validate_month_year(month, year)
        
        # Create cache key
        cache_key = f"user_{user_id}_summary_{month}_{year}"
        
        # Check cache
        cached = cache.get(cache_key)
        if cached:
            return jsonify(cached)
        
        # Get summary
        summary = expense_service.get_summary(user_id, month, year)
        
        # Cache result
        cache.set(cache_key, summary)
        
        return jsonify(summary)
        
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        app.logger.error(f"Get summary error: {e}")
        return error_response('Failed to fetch summary', 500)

@app.route('/get_monthly_trend')
@login_required
def get_monthly_trend():
    """Returns total spending grouped by month."""
    try:
        user_id = session['user_id']
        cache_key = f"user_{user_id}_monthly_trend"
        
        # Check cache
        cached = cache.get(cache_key)
        if cached:
            return jsonify(cached)
        
        # Get trend
        data = expense_service.get_monthly_trend(user_id)
        
        # Cache result
        cache.set(cache_key, data)
        
        return jsonify(data)
        
    except Exception as e:
        app.logger.error(f"Get monthly trend error: {e}")
        return error_response('Failed to fetch monthly trend', 500)

# Investment Routes
@app.route('/investments')
@login_required
def investments():
    """Investment page UI."""
    return render_template('investments.html')

@app.route('/add_investment', methods=['POST'])
@login_required
@rate_limit(max_requests=30, window_seconds=60)
def add_investment():
    """Add a new investment."""
    try:
        data = request.get_json() or request.form
        user_id = session['user_id']
        
        # Validate inputs
        asset = validate_string(data.get('asset', ''), 'Asset')
        value = validate_numeric(data.get('value'), 'Value')
        date = validate_date(data.get('date'))
        
        # Add investment
        investment_id = investment_service.add_investment(
            user_id, asset, value, date
        )
        
        # Invalidate cache
        cache.invalidate(f"user_{user_id}")
        
        app.logger.info(f"Investment added: {investment_id} for user {user_id}")
        return success_response('Investment added successfully!', {'id': investment_id})
        
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        app.logger.error(f"Add investment error: {e}")
        return error_response('Failed to add investment', 500)

@app.route('/get_investments')
@login_required
def get_investments():
    """Get investments grouped by asset."""
    try:
        user_id = session['user_id']
        cache_key = f"user_{user_id}_investments_summary"
        
        # Check cache
        cached = cache.get(cache_key)
        if cached:
            return jsonify(cached)
        
        # Get summary
        data = investment_service.get_summary(user_id)
        
        # Cache result
        cache.set(cache_key, data)
        
        return jsonify(data)
        
    except Exception as e:
        app.logger.error(f"Get investments error: {e}")
        return error_response('Failed to fetch investments', 500)

@app.route('/get_investments_full')
@login_required
def get_investments_full():
    """Get all investments with optional month/year filtering."""
    try:
        user_id = session['user_id']
        month = request.args.get('month')
        year = request.args.get('year')
        
        # Validate filters
        if month or year:
            month, year = validate_month_year(month, year)
        
        # Get investments
        investments = investment_service.get_investments(user_id, month, year)
        
        return jsonify(investments)
        
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        app.logger.error(f"Get investments full error: {e}")
        return error_response('Failed to fetch investments', 500)

@app.route('/update_investment/<int:investment_id>', methods=['POST'])
@login_required
@rate_limit(max_requests=30, window_seconds=60)
def update_investment(investment_id):
    """Update an existing investment."""
    try:
        data = request.get_json() or request.form
        user_id = session['user_id']
        
        # Validate inputs
        asset = validate_string(data.get('asset', ''), 'Asset')
        value = validate_numeric(data.get('value'), 'Value')
        date = validate_date(data.get('date'))
        
        # Update investment
        success = investment_service.update_investment(
            investment_id, user_id, asset, value, date
        )
        
        if not success:
            return error_response('Investment not found or unauthorized', 404)
        
        # Invalidate cache
        cache.invalidate(f"user_{user_id}")
        
        app.logger.info(f"Investment updated: {investment_id} for user {user_id}")
        return success_response('Investment updated successfully!')
        
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        app.logger.error(f"Update investment error: {e}")
        return error_response('Failed to update investment', 500)

@app.route('/delete_investment/<int:investment_id>', methods=['DELETE'])
@login_required
@rate_limit(max_requests=30, window_seconds=60)
def delete_investment(investment_id):
    """Delete an investment."""
    try:
        user_id = session['user_id']
        
        success = investment_service.delete_investment(investment_id, user_id)
        
        if not success:
            return error_response('Investment not found or unauthorized', 404)
        
        # Invalidate cache
        cache.invalidate(f"user_{user_id}")
        
        app.logger.info(f"Investment deleted: {investment_id} for user {user_id}")
        return success_response('Investment deleted successfully!')
        
    except Exception as e:
        app.logger.error(f"Delete investment error: {e}")
        return error_response('Failed to delete investment', 500)

@app.route('/get_investment_trend')
@login_required
def get_investment_trend():
    """Get investment trend over time."""
    try:
        user_id = session['user_id']
        period = request.args.get('period', 'month')
        
        if period not in ['month', 'year']:
            return error_response('Invalid period. Use "month" or "year"', 400)
        
        cache_key = f"user_{user_id}_investment_trend_{period}"
        
        # Check cache
        cached = cache.get(cache_key)
        if cached:
            return jsonify(cached)
        
        # Get trend
        data = investment_service.get_trend(user_id, period)
        
        # Cache result
        cache.set(cache_key, data)
        
        return jsonify(data)
        
    except Exception as e:
        app.logger.error(f"Get investment trend error: {e}")
        return error_response('Failed to fetch investment trend', 500)

if __name__ == '__main__':
    app.run(debug=True)