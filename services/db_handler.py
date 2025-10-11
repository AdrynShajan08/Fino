import sqlite3

def create_tables(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Users table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')

    # Expenses (linked to user)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            category TEXT,
            amount REAL,
            date TEXT,
            description TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Investments (linked to user)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS investments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            asset TEXT,
            value REAL,
            date TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    conn.commit()
    conn.close()

# def add_expense(db_path, user_id, category, amount, date, description):
#     conn = sqlite3.connect(db_path)
#     cur = conn.cursor()
#     cur.execute('INSERT INTO expenses (user_id, category, amount, date, description) VALUES (?, ?, ?, ?, ?)',
#                 (user_id, category, amount, date, description))
#     conn.commit()
#     conn.close()

def get_summary_data(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('SELECT category, SUM(amount) FROM expenses GROUP BY category')
    data = cur.fetchall()
    conn.close()
    return [{'category': row[0], 'total': row[1]} for row in data]


