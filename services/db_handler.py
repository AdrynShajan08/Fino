"""
Database initialization and setup with optimizations.
"""
import sqlite3

def create_tables(db_path):
    """
    Create all necessary database tables.
    
    Args:
        db_path: Path to SQLite database
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Users table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    ''')

    # Expenses table (linked to user)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL CHECK(amount >= 0),
            date TEXT NOT NULL,
            description TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # Investments table (linked to user)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS investments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            asset TEXT NOT NULL,
            value REAL NOT NULL CHECK(value >= 0),
            date TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    conn.commit()
    conn.close()

def create_indexes(db_path):
    """
    Create database indexes for better query performance.
    
    Args:
        db_path: Path to SQLite database
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Indexes for expenses table
    cur.execute('CREATE INDEX IF NOT EXISTS idx_expenses_user ON expenses(user_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses(user_id, date)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_expenses_user_category ON expenses(user_id, category)')
    
    # Indexes for investments table
    cur.execute('CREATE INDEX IF NOT EXISTS idx_investments_user ON investments(user_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_investments_date ON investments(date)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_investments_asset ON investments(asset)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_investments_user_date ON investments(user_id, date)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_investments_user_asset ON investments(user_id, asset)')
    
    # Index for users table
    cur.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
    
    conn.commit()
    conn.close()

def optimize_database(db_path):
    """
    Run SQLite optimization commands.
    
    Args:
        db_path: Path to SQLite database
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Enable foreign keys
    cur.execute('PRAGMA foreign_keys = ON')
    
    # Optimize database
    cur.execute('PRAGMA optimize')
    
    # Analyze tables for query planner
    cur.execute('ANALYZE')
    
    conn.commit()
    conn.close()

def initialize_database(db_path):
    """
    Initialize database with tables, indexes, and optimizations.
    
    Args:
        db_path: Path to SQLite database
    """
    create_tables(db_path)
    create_indexes(db_path)
    optimize_database(db_path)

def get_summary_data(db_path):
    """
    Get expense summary data (legacy function for compatibility).
    
    Args:
        db_path: Path to SQLite database
    
    Returns:
        list: List of category summaries
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('SELECT category, SUM(amount) FROM expenses GROUP BY category')
    data = cur.fetchall()
    conn.close()
    return [{'category': row[0], 'total': row[1]} for row in data]