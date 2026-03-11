"""EVA's task tool — tracks self-directed goals and progress."""

from langchain_core.tools import tool
from config import logger
from typing import Literal
from eva.core.tasks import TaskDB

_task_db: TaskDB | None = None

def init(task_db: TaskDB):
    global _task_db
    _task_db = task_db


@tool
async def task(
    action: Literal['create', 'check', 'update', 'done'], 
    content: str = "", 
    task_id: str = ""
) -> str:
    """
    I use this to manage my tasks. Select ONE action:
    - 'create': content = a specific, actionable objective I can complete and verify
    - 'update': content = my progress notes, task_id = id
    - 'check': returns all open tasks
    - 'done': task_id 
    """
    if _task_db is None:
        logger.error("Task Tool: Task DB is not initialized.")
        return "I am tired, cannot run tasks."

    if action == "create":
        task_id = await _task_db.create(content.strip())
        return f"I created a task: '{task_id}' - {content.strip()}"

    if action == "check":
        tasks = await _task_db.get_open()
        if not tasks:
            return "I have nothing planned right now."
        lines = []
        for t in tasks:
            line = f"[{t['status']}] {t['task_id']}: {t['objective']}"
            if t["scratchpad"]:
                line += f"\n  Notes: {t['scratchpad']}"
            lines.append(line)
        return "\n".join(lines)
    
    if action == "update":
        if not task_id:
            return "I have find the 'task_id' for update."
        await _task_db.update(task_id.strip(), content.strip())
        return f"I updated task '{task_id}': {content.strip()}."

    if action == "done":
        if not task_id:
            return "Must provide a 'task_id' to mark as done."
        await _task_db.complete(task_id.strip())
        return f"I completed task {task_id.strip()}."

    return f"I can't '{action}'. Use only one of ['create', 'check', 'update', 'done']."
