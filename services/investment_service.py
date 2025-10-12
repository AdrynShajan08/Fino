"""
Investment service layer for business logic.
"""
import sqlite3
from contextlib import contextmanager

class InvestmentService:
    """Service class for investment operations."""
    
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
    
    def add_investment(self, user_id, asset, value, date):
        """
        Add a new investment.
        
        Args:
            user_id: ID of the user
            asset: Investment asset name
            value: Investment value
            date: Date of investment (YYYY-MM-DD)
        
        Returns:
            int: ID of the created investment
        """
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                '''INSERT INTO investments (user_id, asset, value, date) 
                   VALUES (?, ?, ?, ?)''',
                (user_id, asset, value, date)
            )
            return cur.lastrowid
    
    def get_investments(self, user_id, month=None, year=None):
        """
        Get investments for a user with optional filtering.
        
        Args:
            user_id: ID of the user
            month: Optional month filter (MM format)
            year: Optional year filter (YYYY format)
        
        Returns:
            list: List of investment dictionaries
        """
        query = 'SELECT * FROM investments WHERE user_id = ?'
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
    
    def get_investment_by_id(self, investment_id, user_id):
        """
        Get a specific investment by ID.
        
        Args:
            investment_id: ID of the investment
            user_id: ID of the user (for authorization)
        
        Returns:
            dict: Investment data or None if not found
        """
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                'SELECT * FROM investments WHERE id = ? AND user_id = ?',
                (investment_id, user_id)
            )
            row = cur.fetchone()
            return dict(row) if row else None
    
    def update_investment(self, investment_id, user_id, asset, value, date):
        """
        Update an existing investment.
        
        Args:
            investment_id: ID of the investment
            user_id: ID of the user (for authorization)
            asset: Updated asset name
            value: Updated value
            date: Updated date
        
        Returns:
            bool: True if updated, False if not found
        """
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                '''UPDATE investments 
                   SET asset = ?, value = ?, date = ? 
                   WHERE id = ? AND user_id = ?''',
                (asset, value, date, investment_id, user_id)
            )
            return cur.rowcount > 0
    
    def delete_investment(self, investment_id, user_id):
        """
        Delete an investment.
        
        Args:
            investment_id: ID of the investment
            user_id: ID of the user (for authorization)
        
        Returns:
            bool: True if deleted, False if not found
        """
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                'DELETE FROM investments WHERE id = ? AND user_id = ?',
                (investment_id, user_id)
            )
            return cur.rowcount > 0
    
    def get_summary(self, user_id):
        """
        Get investment summary grouped by asset.
        
        Args:
            user_id: ID of the user
        
        Returns:
            list: List of {asset, value} dictionaries
        """
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                '''SELECT asset, SUM(value) as total 
                   FROM investments 
                   WHERE user_id = ? 
                   GROUP BY asset''',
                (user_id,)
            )
            return [
                {'asset': row['asset'], 'value': row['total']}
                for row in cur.fetchall()
            ]
    
    def get_trend(self, user_id, period='month'):
        """
        Get investment trend over time.
        
        Args:
            user_id: ID of the user
            period: 'month' or 'year'
        
        Returns:
            dict: Trend data with labels and values
        """
        with self.get_connection() as conn:
            cur = conn.cursor()
            
            if period == 'year':
                cur.execute("""
                    SELECT strftime('%Y', date) as period, SUM(value) as total_value
                    FROM investments
                    WHERE user_id = ?
                    GROUP BY strftime('%Y', date)
                    ORDER BY period
                """, (user_id,))
            else:  # month
                cur.execute("""
                    SELECT strftime('%Y-%m', date) as period, SUM(value) as total_value
                    FROM investments
                    WHERE user_id = ?
                    GROUP BY strftime('%Y-%m', date)
                    ORDER BY period
                """, (user_id,))
            
            rows = cur.fetchall()
            labels = [row['period'] for row in rows]
            values = [row['total_value'] for row in rows]
            
            return {'labels': labels, 'values': values}
    
    def get_total_investments(self, user_id):
        """
        Get total investments for a user.
        
        Args:
            user_id: ID of the user
        
        Returns:
            float: Total investments
        """
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                'SELECT COALESCE(SUM(value), 0) as total FROM investments WHERE user_id = ?',
                (user_id,)
            )
            return cur.fetchone()['total']