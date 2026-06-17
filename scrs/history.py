import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

DB_PATH = Path("data/history.db")


class ConversationHistory:
    def __init__(self):
        self.db_path = str(DB_PATH)
        self._init_db()

    def _init_db(self):
        """ایجاد جدول تاریخچه"""
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    source_count INTEGER DEFAULT 0
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_session ON conversations(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_time ON conversations(timestamp DESC)")

    def add(self, question: str, answer: str, session_id: str = "default", source_count: int = 0):
        """اضافه کردن مکالمه جدید"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO conversations (session_id, timestamp, question, answer, source_count) VALUES (?, ?, ?, ?, ?)",
                (session_id, datetime.now().isoformat(), question, answer, source_count)
            )

    def get_by_session(self, session_id: str, limit: int = 50) -> List[Dict]:
        """گرفتن تاریخچه یک جلسه"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT id, question, answer, timestamp, source_count FROM conversations WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
                (session_id, limit)
            )
            return [dict(row) for row in cursor.fetchall()]

    def clear_session(self, session_id: str):
        """پاک کردن تاریخچه یک جلسه"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))

    def get_stats(self) -> Dict:
        """آمار کلی"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) as total FROM conversations")
            total = cursor.fetchone()[0]
            return {"total_conversations": total}


history = ConversationHistory()