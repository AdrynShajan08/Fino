import sqlite3
from datetime import datetime

def monthly_summary(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    month = datetime.now().strftime('%Y-%m')
    cur.execute('SELECT category, SUM(amount) FROM expenses WHERE date LIKE ? GROUP BY category', (f'{month}%',))
    data = cur.fetchall()
    conn.close()
    summary = [{'category': row[0], 'total': row[1]} for row in data]
    return summary
