"""SQLite database operations for storing booking requests."""
import sqlite3
import datetime
from typing import List, Dict, Optional


class Database:
    def __init__(self, db_path: str = "bookings.db"):
        """Initialize database connection and create tables if needed."""
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Create the requests table if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            chat_id TEXT NOT NULL,
            requested_date TEXT NOT NULL,
            requested_time TEXT NOT NULL,
            court_preference TEXT,
            duration INTEGER, 
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL,
            processed_at TEXT,
            result_message TEXT
            )
        """)
        conn.commit()
        conn.close()
    
    def add_request(self, user_id: str, chat_id: str, requested_date: str, 
                   requested_time: str, court_preference: Optional[str] = None, duration: int = 90) -> int:
        """Add a new booking request to the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        created_at = datetime.datetime.now().isoformat()
        cursor.execute("""
                INSERT INTO requests (user_id, chat_id, requested_date, requested_time, 
                                    court_preference, duration, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
            """, (user_id, chat_id, requested_date, requested_time, 
                court_preference, duration, created_at))
        request_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return request_id
    
    def get_pending_requests(self) -> List[Dict]:
        """Get all pending booking requests."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM requests WHERE status = 'pending' ORDER BY created_at
        """)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def get_requests_for_date(self, target_date: str) -> List[Dict]:
        """Get pending requests for a specific date."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM requests 
            WHERE status = 'pending' AND requested_date = ?
            ORDER BY created_at
        """, (target_date,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def get_user_requests(self, user_id: str) -> List[Dict]:
        """Get all requests for a specific user."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM requests 
            WHERE user_id = ? 
            ORDER BY created_at DESC
        """, (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def update_request_status(self, request_id: int, status: str, 
                            result_message: Optional[str] = None):
        """Update the status of a booking request."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        processed_at = datetime.datetime.now().isoformat()
        cursor.execute("""
            UPDATE requests 
            SET status = ?, processed_at = ?, result_message = ?
            WHERE id = ?
        """, (status, processed_at, result_message, request_id))
        conn.commit()
        conn.close()
    
    def cancel_request(self, request_id: int, user_id: str) -> bool:
        """Cancel a pending request. Returns True if successful."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE requests 
            SET status = 'cancelled'
            WHERE id = ? AND user_id = ? AND status = 'pending'
        """, (request_id, user_id))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def get_request(self, request_id: int) -> Optional[Dict]:
        """Get a specific request by ID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM requests WHERE id = ?", (request_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
