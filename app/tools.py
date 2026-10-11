from datetime import datetime
from app.database import get_db


def get_current_time():

    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def create_task(title, description=""):

    with get_db() as db:

        cursor = db.execute(
            """
            INSERT INTO tasks(title, description)
            VALUES (?, ?)
            """,
            (title, description)
        )

        db.commit()

        return {
            "id": cursor.lastrowid,
            "title": title,
            "description": description,
            "status": "pending"
        }


def list_tasks():

    with get_db() as db:

        rows = db.execute(
            """
            SELECT *
            FROM tasks
            ORDER BY id DESC
            """
        ).fetchall()

        return [dict(row) for row in rows]


def complete_task(task_id):

    with get_db() as db:

        cursor = db.execute(
            """
            UPDATE tasks
            SET status = 'completed'
            WHERE id = ?
            """,
            (task_id,)
        )

        db.commit()

        return cursor.rowcount > 0


def get_tools():

    return {
        "get_current_time": get_current_time,
        "create_task": create_task,
        "list_tasks": list_tasks,
        "complete_task": complete_task
    }