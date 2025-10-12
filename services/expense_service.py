"""
Expense service layer for business logic.
"""
import sqlite3
from contextlib import contextmanager

class ExpenseService:
    """Service class for expense operations."""
    
    def __init__(self, db_path):
        """
        Initialize service.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def add_expense(self, user_id, category, amount, date, description=''):
        """
        Add a new expense.
        
        Args:
            user_id: ID of the user
            category: Expense category
            amount: Expense amount
            date: Date of expense (YYYY-MM-DD)
            description: Optional description
        
        Returns:
            int: ID of the created expense
        """
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                '''INSERT INTO expenses (user_id, category, amount, date, description) 
                   VALUES (?, ?, ?, ?, ?)''',
                (user_id, category, amount, date, description)
            )
            return cur.lastrowid
    
    def get_expenses(self, user_id, month=None, year=None):
        """
        Get expenses for a user with optional filtering.
        
        Args:
            user_id: ID of the user
            month: Optional month filter (MM format)
            year: Optional year filter (YYYY format)
        
        Returns:
            list: List of expense dictionaries
        """
        query = 'SELECT * FROM expenses WHERE user_id = ?'
        params = [user_id]
        
        if month and year:
            query += ' AND strftime("%m", date) = ? AND strftime("%Y", date) = ?'
            params.extend([month, year])
        elif year:
            query += ' AND strftime("%Y", date) = ?'
            params.append(year)
        
        query += ' ORDER BY date DESC'
        
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]
    
    def get_expense_by_id(self, expense_id, user_id):
        """
        Get a specific expense by ID.
        
        Args:
            expense_id: ID of the expense
            user_id: ID of the user (for authorization)
        
        Returns:
            dict: Expense data or None if not found
        """
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                'SELECT * FROM expenses WHERE id = ? AND user_id = ?',
                (expense_id, user_id)
            )
            row = cur.fetchone()
            return dict(row) if row else None
    
    def update_expense(self, expense_id, user_id, category, amount, date, description=''):
        """
        Update an existing expense.
        
        Args:
            expense_id: ID of the expense
            user_id: ID of the user (for authorization)
            category: Updated category
            amount: Updated amount
            date: Updated date
            description: Updated description
        
        Returns:
            bool: True if updated, False if not found
        """
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                '''UPDATE expenses 
                   SET category = ?, amount = ?, date = ?, description = ? 
                   WHERE id = ? AND user_id = ?''',
                (category, amount, date, description, expense_id, user_id)
            )
            return cur.rowcount > 0
    
    def delete_expense(self, expense_id, user_id):
        """
        Delete an expense.
        
        Args:
            expense_id: ID of the expense
            user_id: ID of the user (for authorization)
        
        Returns:
            bool: True if deleted, False if not found
        """
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                'DELETE FROM expenses WHERE id = ? AND user_id = ?',
                (expense_id, user_id)
            )
            return cur.rowcount > 0
    
    def get_summary(self, user_id, month=None, year=None):
        """
        Get expense summary grouped by category.
        
        Args:
            user_id: ID of the user
            month: Optional month filter (MM format)
            year: Optional year filter (YYYY format)
        
        Returns:
            dict: Summary with labels and values
        """
        query = '''SELECT category, SUM(amount) as total 
                   FROM expenses 
                   WHERE user_id = ?'''
        params = [user_id]
        
        if month and year:
            query += ' AND strftime("%m", date) = ? AND strftime("%Y", date) = ?'
            params.extend([month, year])
        elif year:
            query += ' AND strftime("%Y", date) = ?'
            params.append(year)
        
        query += ' GROUP BY category'
        
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            rows = cur.fetchall()
        
        labels = [row['category'] for row in rows]
        values = [row['total'] for row in rows]
        
        return {'labels': labels, 'values': values}
    
    def get_monthly_trend(self, user_id):
        """
        Get monthly spending trend.
        
        Args:
            user_id: ID of the user
        
        Returns:
            list: List of {month, total} dictionaries
        """
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT strftime('%Y-%m', date) AS month, SUM(amount) as total
                FROM expenses
                WHERE user_id = ?
                GROUP BY month
                ORDER BY month
            """, (user_id,))
            return [dict(row) for row in cur.fetchall()]
    
    def get_total_expenses(self, user_id):
        """
        Get total expenses for a user.
        
        Args:
            user_id: ID of the user
        
        Returns:
            float: Total expenses
        """
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                'SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE user_id = ?',
                (user_id,)
            )
            return cur.fetchone()['total']