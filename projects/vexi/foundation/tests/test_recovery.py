# Shared imports work in both source (core/) and installed flat layouts.
import sys as _sys
from pathlib import Path as _Path
_root = _Path(__file__).resolve().parents[2]
_sys.path.insert(0, str(_root / "core" if (_root / "core").is_dir() else _root))
import sys
from pathlib import Path
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "core"))
from vexi_foundation.contracts import Actor, Scope, SpeakerRole
from vexi_foundation.attention import TaskSession, TaskState
from vexi_foundation.task_store import TaskStore
from foundation_bridge import FoundationBridge


class RecoveryTests(unittest.TestCase):
    def test_actor_switch_does_not_erase_owner_task(self):
        b = FoundationBridge({})
        owner = Actor("owner", "owner", SpeakerRole.OWNER)
        b.execute("привет", actor=owner)
        original = b.task
        b.execute("привет")
        b.execute("ты тут", actor=owner)
        self.assertIs(b.task, original)
        self.assertEqual(original.state, TaskState.ACTIVE)

    def test_restart_suspends_and_discards_authority_and_targets(self):
        actor, scope = Actor("owner", "new-session", SpeakerRole.OWNER), Scope("t", "p")
        task = TaskSession("task-1", actor, scope, "opaque-goal", last_target_ref="old-target")
        with tempfile.TemporaryDirectory() as tmp:
            store = TaskStore(Path(tmp)); store.save(task)
            restored = store.restore("task-1", actor, scope)
            self.assertEqual(restored.state, TaskState.SUSPENDED)
            self.assertIsNone(restored.last_target_ref)
            with self.assertRaises(PermissionError):
                store.restore("task-1", Actor("guest", "x"), scope)

    def test_terminal_checkpoint_remains_terminal(self):
        actor, scope = Actor("owner", "session"), Scope("t", "p")
        task = TaskSession("task", actor, scope, "goal")
        task.transition(TaskState.COMPLETED, explicit=True)
        with tempfile.TemporaryDirectory() as tmp:
            store = TaskStore(Path(tmp)); store.save(task)
            self.assertEqual(store.restore("task", actor, scope).state, TaskState.COMPLETED)

    def test_corrupt_checkpoint_is_not_silently_reset(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "task.json").write_text("{broken")
            with self.assertRaises(ValueError):
                TaskStore(Path(tmp)).restore("task", Actor("x", "x"), Scope("t", "p"))
