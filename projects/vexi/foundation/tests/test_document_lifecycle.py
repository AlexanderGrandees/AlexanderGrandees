# Shared imports work in both source (core/) and installed flat layouts.
import sys as _sys
from pathlib import Path as _Path
_root = _Path(__file__).resolve().parents[2]
_sys.path.insert(0, str(_root / "core" if (_root / "core").is_dir() else _root))
import json
from pathlib import Path
import tempfile
import unittest

from vexi_foundation.contracts import Scope
from vexi_foundation.integrity import Materiality
from vexi_foundation.workspace import DocumentRecord
from vexi_foundation.document_lifecycle import (
    DocumentLifecycle, LifecycleError, LocalDocumentLifecycleStore,
)


class DocumentLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = LocalDocumentLifecycleStore(self.root / "state")
        self.scope = Scope("tenant-a", "project-a")
        self.other = Scope("tenant-a", "project-b")
        self.record = DocumentRecord(
            document_id="doc-001",
            scope=self.scope,
            relative_path="drafts/test.md",
            document_type="NOTE",
            object_refs=("client:1",),
            canonical_version=None,
            working_revision="",
            content_hash="",
            lifecycle="DRAFT",
            stale=False,
        )

    def tearDown(self):
        self.temp.cleanup()

    def register(self, content=b"alpha"):
        return self.store.register(self.record, initial_content=content, now=100.0)

    def test_register_and_readback(self):
        state = self.register()
        self.assertEqual(state.generation, 1)
        self.assertEqual(state.working.revision_id, "w000001")
        self.assertEqual(self.store.read_working("doc-001", self.scope), b"alpha")
        self.store.verify("doc-001", self.scope)

    def test_duplicate_identity_is_blocked(self):
        self.register()
        with self.assertRaisesRegex(LifecycleError, "document_exists"):
            self.store.register(self.record, initial_content=b"beta", now=101.0)

    def test_scope_is_hard_boundary_without_identity_disclosure(self):
        self.register()
        with self.assertRaisesRegex(LifecycleError, "document_not_found"):
            self.store.load("doc-001", self.other)

    def test_same_document_id_can_exist_in_two_scopes(self):
        first = self.register(b"alpha")
        other_record = DocumentRecord(
            document_id="doc-001", scope=self.other, relative_path="drafts/test.md",
            document_type="NOTE", object_refs=("client:2",), canonical_version=None,
            working_revision="", content_hash="", lifecycle="DRAFT", stale=False)
        second = self.store.register(other_record, initial_content=b"alpha", now=100.0)
        self.assertEqual(first.record.document_id, second.record.document_id)
        self.assertNotEqual(self.store._scope_key(self.scope), self.store._scope_key(self.other))
        self.assertEqual(self.store.read_working("doc-001", self.scope), b"alpha")
        self.assertEqual(self.store.read_working("doc-001", self.other), b"alpha")

    def test_autosave_is_working_revision_not_formal_version(self):
        state = self.register()
        state = self.store.autosave("doc-001", self.scope, content=b"beta",
                                    expected_generation=state.generation,
                                    change_summary="typing", now=101.0)
        self.assertEqual(state.working.revision_id, "w000002")
        self.assertEqual(state.versions, ())
        self.assertIsNone(state.record.canonical_version)

    def test_identical_autosave_is_noop(self):
        state = self.register()
        same = self.store.autosave("doc-001", self.scope, content=b"alpha",
                                   expected_generation=state.generation, now=101.0)
        self.assertEqual(same.generation, state.generation)

    def test_material_checkpoint_creates_immutable_version(self):
        state = self.register()
        result = self.store.checkpoint(
            "doc-001", self.scope, expected_generation=state.generation,
            materiality=Materiality.CONTENT, change_summary="first checkpoint", now=102.0)
        self.assertEqual(result.code, "version_created")
        self.assertEqual(result.version.version_id, "v000001")
        self.assertIsNone(result.state.record.canonical_version)
        self.assertEqual(self.store.read_version("doc-001", self.scope, "v000001"), b"alpha")

    def test_cosmetic_checkpoint_does_not_spam_versions(self):
        state = self.register()
        result = self.store.checkpoint(
            "doc-001", self.scope, expected_generation=state.generation,
            materiality=Materiality.COSMETIC, change_summary="formatting", now=102.0)
        self.assertEqual(result.code, "cosmetic_kept_working")
        self.assertEqual(result.state.generation, state.generation)
        self.assertEqual(result.state.versions, ())

    def test_canonical_promotion_is_explicit_and_optimistic(self):
        state = self.register()
        cp = self.store.checkpoint(
            "doc-001", self.scope, expected_generation=state.generation,
            materiality=Materiality.CONTENT, change_summary="checkpoint", now=102.0)
        state = self.store.promote_canonical(
            "doc-001", self.scope, version_id="v000001", expected_canonical=None,
            expected_generation=cp.state.generation, now=103.0)
        self.assertEqual(state.record.canonical_version, "v000001")
        self.assertFalse(state.record.stale)
        with self.assertRaisesRegex(LifecycleError, "generation_conflict"):
            self.store.promote_canonical(
                "doc-001", self.scope, version_id="v000001", expected_canonical=None,
                expected_generation=cp.state.generation, now=104.0)

    def test_restore_old_version_creates_new_working_revision_only(self):
        state = self.register(b"one")
        cp1 = self.store.checkpoint(
            "doc-001", self.scope, expected_generation=state.generation,
            materiality=Materiality.CONTENT, change_summary="one", now=101.0)
        state = self.store.promote_canonical(
            "doc-001", self.scope, version_id="v000001", expected_canonical=None,
            expected_generation=cp1.state.generation, now=102.0)
        state = self.store.autosave(
            "doc-001", self.scope, content=b"two", expected_generation=state.generation,
            change_summary="two", now=103.0)
        cp2 = self.store.checkpoint(
            "doc-001", self.scope, expected_generation=state.generation,
            materiality=Materiality.BUSINESS_MATERIAL, change_summary="two", now=104.0)
        state = self.store.promote_canonical(
            "doc-001", self.scope, version_id="v000002", expected_canonical="v000001",
            expected_generation=cp2.state.generation, now=105.0)
        restored = self.store.restore_as_working(
            "doc-001", self.scope, version_id="v000001",
            expected_generation=state.generation, now=106.0)
        self.assertEqual(restored.record.canonical_version, "v000002")
        self.assertEqual(self.store.read_working("doc-001", self.scope), b"one")

    def test_stale_blocks_approved_transition_until_new_canonical(self):
        state = self.register()
        cp = self.store.checkpoint(
            "doc-001", self.scope, expected_generation=state.generation,
            materiality=Materiality.CONTENT, change_summary="checkpoint", now=101.0)
        state = self.store.promote_canonical(
            "doc-001", self.scope, version_id="v000001", expected_canonical=None,
            expected_generation=cp.state.generation, now=102.0)
        state = self.store.transition_lifecycle(
            "doc-001", self.scope, target=DocumentLifecycle.REVIEW,
            expected_generation=state.generation, now=103.0)
        state = self.store.mark_stale(
            "doc-001", self.scope, expected_generation=state.generation,
            reason_ref="source:changed", now=104.0)
        with self.assertRaisesRegex(LifecycleError, "canonical_required"):
            self.store.transition_lifecycle(
                "doc-001", self.scope, target=DocumentLifecycle.APPROVED,
                expected_generation=state.generation, now=105.0)

    def test_metadata_checksum_detects_corruption(self):
        self.register()
        path = self.store._meta_path(self.scope, "doc-001")
        envelope = json.loads(path.read_text("utf-8"))
        envelope["payload"]["generation"] = 999
        path.write_text(json.dumps(envelope), encoding="utf-8")
        with self.assertRaisesRegex(LifecycleError, "metadata_integrity"):
            self.store.load("doc-001", self.scope)

    def test_blob_tamper_is_detected(self):
        state = self.register()
        blob = next((self.root / "state" / "blobs" / self.store._scope_key(self.scope)).glob("*/*.bin"))
        blob.write_bytes(b"tampered")
        with self.assertRaisesRegex(LifecycleError, "blob_integrity"):
            self.store.verify("doc-001", self.scope)

    def test_lock_is_fail_closed_and_explicit_recovery_only(self):
        self.register()
        lock = self.store._lock_path(self.scope, "doc-001")
        lock.write_text("synthetic", encoding="utf-8")
        with self.assertRaisesRegex(LifecycleError, "document_locked"):
            self.store.autosave("doc-001", self.scope, content=b"beta",
                                expected_generation=1, now=101.0)
        # Fresh synthetic lock must not be silently removed.
        with self.assertRaisesRegex(LifecycleError, "lock_not_stale"):
            self.store.clear_stale_lock("doc-001", self.scope,
                                        now=lock.stat().st_mtime + 1, stale_after=60)
        self.assertTrue(self.store.clear_stale_lock(
            "doc-001", self.scope, now=lock.stat().st_mtime + 61, stale_after=60))

    def test_orphan_blob_is_visible_but_not_promoted(self):
        self.register()
        orphan_hash = self.store._put_blob(self.scope, b"orphan")
        self.assertIn(orphan_hash, self.store.list_orphan_blobs(self.scope))
        state = self.store.load("doc-001", self.scope)
        self.assertNotEqual(state.record.content_hash, orphan_hash)


    def test_verify_allows_working_to_diverge_from_canonical(self):
        state = self.register(b"one")
        cp = self.store.checkpoint(
            "doc-001", self.scope, expected_generation=state.generation,
            materiality=Materiality.CONTENT, change_summary="one", now=101.0)
        state = self.store.promote_canonical(
            "doc-001", self.scope, version_id="v000001", expected_canonical=None,
            expected_generation=cp.state.generation, now=102.0)
        state = self.store.autosave(
            "doc-001", self.scope, content=b"two", expected_generation=state.generation,
            change_summary="editing after canonical", now=103.0)
        verified = self.store.verify("doc-001", self.scope)
        self.assertEqual(verified.record.canonical_version, "v000001")
        self.assertEqual(verified.working.content_hash, verified.record.content_hash)
        self.assertNotEqual(verified.working.content_hash, verified.version("v000001").content_hash)

    def test_stale_cannot_be_cleared_by_repromoting_same_canonical(self):
        state = self.register(b"one")
        cp = self.store.checkpoint(
            "doc-001", self.scope, expected_generation=state.generation,
            materiality=Materiality.CONTENT, change_summary="one", now=101.0)
        state = self.store.promote_canonical(
            "doc-001", self.scope, version_id="v000001", expected_canonical=None,
            expected_generation=cp.state.generation, now=102.0)
        state = self.store.mark_stale(
            "doc-001", self.scope, expected_generation=state.generation,
            reason_ref="source:changed", now=103.0)
        with self.assertRaisesRegex(LifecycleError, "stale_requires_revalidation"):
            self.store.promote_canonical(
                "doc-001", self.scope, version_id="v000001", expected_canonical="v000001",
                expected_generation=state.generation, now=104.0)

    def test_canonical_promotion_requires_current_working_checkpoint(self):
        state = self.register(b"one")
        cp = self.store.checkpoint(
            "doc-001", self.scope, expected_generation=state.generation,
            materiality=Materiality.CONTENT, change_summary="one", now=101.0)
        state = self.store.autosave(
            "doc-001", self.scope, content=b"two", expected_generation=cp.state.generation,
            change_summary="new working", now=102.0)
        with self.assertRaisesRegex(LifecycleError, "canonical_requires_current_checkpoint"):
            self.store.promote_canonical(
                "doc-001", self.scope, version_id="v000001", expected_canonical=None,
                expected_generation=state.generation, now=103.0)

    def test_approved_requires_canonical(self):
        state = self.register()
        state = self.store.transition_lifecycle(
            "doc-001", self.scope, target=DocumentLifecycle.REVIEW,
            expected_generation=state.generation, now=101.0)
        with self.assertRaisesRegex(LifecycleError, "canonical_required"):
            self.store.transition_lifecycle(
                "doc-001", self.scope, target=DocumentLifecycle.APPROVED,
                expected_generation=state.generation, now=102.0)


if __name__ == "__main__":
    unittest.main()
