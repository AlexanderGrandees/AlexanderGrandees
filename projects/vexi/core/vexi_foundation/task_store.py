"""Opt-in local metadata checkpoint. Stores references, never utterances/results.

Restores SUSPENDED tasks; authentication, approval and target freshness do not survive
a restart. Configure an owner-protected, non-synced directory before using this store.
"""
import json
import os
import tempfile
from pathlib import Path
from .contracts import Actor, Scope
from .attention import TaskSession, TaskState


class TaskStore:
    def __init__(self, directory: Path):
        self.directory = directory

    def _path(self, task_id):
        if not task_id or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in task_id):
            raise ValueError("invalid_task_id")
        return self.directory / (task_id + ".json")

    def save(self, task: TaskSession):
        target = self._path(task.task_id)
        self.directory.mkdir(parents=True, exist_ok=True)
        # All references must be opaque IDs, not text copied from an utterance.
        payload = {"schema": 1, "task_id": task.task_id, "subject": task.actor.subject,
                   "tenant": task.scope.tenant, "project": task.scope.project,
                   "goal_ref": task.goal_ref, "state": task.state.value, "revision": task.revision}
        fd, temporary = tempfile.mkstemp(dir=self.directory, prefix="checkpoint-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f)
                f.flush(); os.fsync(f.fileno())
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary): os.unlink(temporary)

    def restore(self, task_id: str, actor: Actor, scope: Scope) -> TaskSession:
        raw = json.loads(self._path(task_id).read_text(encoding="utf-8"))
        if (raw["schema"] != 1 or raw["task_id"] != task_id or raw["subject"] != actor.subject
                or raw["tenant"] != scope.tenant or raw["project"] != scope.project):
            raise PermissionError("checkpoint_scope")
        state = TaskState(raw["state"])
        if state not in {TaskState.COMPLETED, TaskState.CANCELLED}:
            state = TaskState.SUSPENDED
        return TaskSession(task_id, actor, scope, raw["goal_ref"], state=state, revision=raw["revision"])
