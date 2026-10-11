from app.database import get_db


class MemoryManager:

    def add(self, content, category="general"):

        if not content.strip():
            raise ValueError("Memory cannot be empty")

        with get_db() as db:

            cursor = db.execute(
                """
                INSERT INTO memories(content, category)
                VALUES (?, ?)
                """,
                (content.strip(), category)
            )

            db.commit()

            return cursor.lastrowid

    def all(self):

        with get_db() as db:

            rows = db.execute(
                """
                SELECT *
                FROM memories
                ORDER BY id DESC
                """
            ).fetchall()

            return [dict(row) for row in rows]

    def get(self, memory_id):

        with get_db() as db:

            row = db.execute(
                """
                SELECT *
                FROM memories
                WHERE id = ?
                """,
                (memory_id,)
            ).fetchone()

            return dict(row) if row else None

    def delete(self, memory_id):

        with get_db() as db:

            cursor = db.execute(
                """
                DELETE FROM memories
                WHERE id = ?
                """,
                (memory_id,)
            )

            db.commit()

            return cursor.rowcount > 0

    def search_keyword(self, keyword):

        with get_db() as db:

            rows = db.execute(
                """
                SELECT *
                FROM memories
                WHERE content LIKE ?
                ORDER BY id DESC
                """,
                (f"%{keyword}%",)
            ).fetchall()

            return [dict(row) for row in rows]
    def __init__(self):
        pass
    def __init__(self):
        self.memories = []
        
memory_manager = MemoryManager()