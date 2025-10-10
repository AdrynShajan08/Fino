import sqlite3

def create_tables(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            category TEXT,
            amount REAL,
            description TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_expense(db_path, date, category, amount, description):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('INSERT INTO expenses (date, category, amount, description) VALUES (?, ?, ?, ?)',
                (date, category, amount, description))
    conn.commit()
    conn.close()

def get_summary_data(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('SELECT category, SUM(amount) FROM expenses GROUP BY category')
    data = cur.fetchall()
    conn.close()
    return [{'category': row[0], 'total': row[1]} for row in data]
