"""EVA's task tool — tracks self-directed goals and progress."""

from langchain_core.tools import tool
from eva.core.tasks import TaskDB

_task_db: TaskDB | None = None


def init(task_db: TaskDB):
    global _task_db
    _task_db = task_db


@tool
async def task(action: str, content: str = "", task_id = "") -> str:
    """
    I use this to manage my tasks. Select ONE action:
    - 'create': content = a specific, actionable objective I can complete and verify
    - 'update': content = my progress notes, task_id = id
    - 'check': returns all open tasks
    - 'done': task_id = id
    """
    if _task_db is None:
        return "Task system not initialized."

    action = action.strip().lower()

    if action == "create":
        task_id = await _task_db.create(content.strip())
        return f"Created task {task_id}: {content.strip()}"

    if action == "check":
        tasks = await _task_db.get_open()
        if not tasks:
            return "No task right now."
        lines = []
        for t in tasks:
            line = f"[{t['status']}] {t['id']}: {t['objective']}"
            if t["scratchpad"]:
                line += f"\n  Notes: {t['scratchpad']}"
            lines.append(line)
        return "\n".join(lines)

    if action == "update":
        if not task_id:
            return "Must provide a 'task_id' to update."
        await _task_db.update(task_id.strip(), content.strip())
        return f"Updated task {task_id.strip()}."

    if action == "done":
        if not task_id:
            return "Must provide a 'task_id' to mark as done."
        await _task_db.complete(task_id.strip())
        return f"Completed task {task_id.strip()}."

    return f"Unknown action '{action}'. Use only one of ['create', 'check', 'update', 'done']."
