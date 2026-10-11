from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.auth.routes import router as auth_router
from app.config import APP_NAME
from app.database import get_db, init_db

from app.models import (
    MemoryCreate,
    TaskCreate,
    ChatRequest,
)

from app.memory.manager import memory_manager
from app.agent import agent

from app.tools import (
    create_task,
    list_tasks,
    complete_task,
)

from app.security import validate_memory


# ==================================================
# PATHS
# ==================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# ==================================================
# FASTAPI APPLICATION
# ==================================================

app = FastAPI(
    title=APP_NAME,
    version="1.0.0",
)


# ==================================================
# AUTHENTICATION ROUTES
# ==================================================

app.include_router(auth_router)


# ==================================================
# DATABASE
# ==================================================

init_db()


# ==================================================
# FRONTEND
# ==================================================

app.mount(
    "/frontend",
    StaticFiles(
        directory=BASE_DIR / "frontend"
    ),
    name="frontend",
)


@app.get(
    "/",
    include_in_schema=False
)
async def home():

    return FileResponse(
        BASE_DIR / "frontend" / "index.html"
    )


# ==================================================
# HEALTH CHECK
# ==================================================

@app.get("/health")
async def health():

    return {
        "status": "online",
        "system": "NEXORA",
    }


# ==================================================
# MEMORY
# ==================================================

@app.post("/memory")
async def save_memory(data: MemoryCreate):

    content = validate_memory(data.content)

    memory_id = memory_manager.add(
        content=content,
        category=data.category
    )

    return memory_manager.get(memory_id)


@app.get("/memory/search")
async def search_memories(q: str = Query(min_length=1, max_length=200)):

    query = q.strip()
    if not query:
        raise HTTPException(
            status_code=400,
            detail="Search query cannot be empty",
        )

    return memory_manager.search_keyword(query)


@app.get("/memory")
async def get_memories():

    return memory_manager.all()


@app.get("/search")
async def search_data(q: str = Query(min_length=1, max_length=200)):

    query = q.strip()
    if not query:
        raise HTTPException(
            status_code=400,
            detail="Search query cannot be empty",
        )

    normalized_query = query.casefold()
    matching_tasks = [
        task
        for task in list_tasks()
        if normalized_query in task["title"].casefold()
        or normalized_query in (task["description"] or "").casefold()
    ]

    return {
        "memories": memory_manager.search_keyword(query),
        "tasks": matching_tasks,
    }


@app.delete("/memory/{memory_id}")
async def delete_memory(memory_id: int):

    if not memory_manager.delete(memory_id):
        raise HTTPException(
            status_code=404,
            detail="Memory not found",
        )

    return {"deleted": True}


# ==================================================
# TASKS
# ==================================================

@app.post("/tasks")
async def create_new_task(data: TaskCreate):

    return create_task(
        title=data.title,
        description=data.description
    )


@app.get("/tasks")
async def get_tasks():

    return list_tasks()


@app.put("/tasks/{task_id}")
async def complete_existing_task(task_id: int):

    return complete_task(task_id)


@app.patch("/tasks/{task_id}")
async def update_task_status(task_id: int, data: dict):

    status = data.get("status")
    if status not in {"pending", "completed"}:
        raise HTTPException(status_code=400, detail="Invalid task status")

    with get_db() as db:
        cursor = db.execute(
            "UPDATE tasks SET status = ? WHERE id = ?",
            (status, task_id),
        )
        db.commit()

    if not cursor.rowcount:
        raise HTTPException(status_code=404, detail="Task not found")

    return {"updated": True, "status": status}


@app.delete("/tasks/{task_id}")
async def delete_existing_task(task_id: int):

    with get_db() as db:
        cursor = db.execute(
            "DELETE FROM tasks WHERE id = ?",
            (task_id,),
        )
        db.commit()

    if not cursor.rowcount:
        raise HTTPException(status_code=404, detail="Task not found")

    return {"deleted": True}


# ==================================================
# AI CHAT
# ==================================================

@app.post("/chat")
async def chat(data: ChatRequest):

    response = agent.chat(
        data.message
    )

    return {
        "response": response
    }


@app.get("/chat/history")
async def get_chat_history(limit: int = Query(default=100, ge=1, le=500)):

    with get_db() as db:
        rows = db.execute(
            """
            SELECT role, content, created_at
            FROM conversations
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in reversed(rows)]