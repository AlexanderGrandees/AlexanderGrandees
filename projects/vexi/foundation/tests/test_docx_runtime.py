# Shared imports work in both source (core/) and installed flat layouts.
import sys as _sys
from pathlib import Path as _Path
_root = _Path(__file__).resolve().parents[2]
_sys.path.insert(0, str(_root / "core" if (_root / "core").is_dir() else _root))
from pathlib import Path
import tempfile
import unittest

from vexi_foundation.contracts import Scope
from vexi_foundation.workspace import DocumentRecord
from vexi_foundation.document_lifecycle import LocalDocumentLifecycleStore
from vexi_foundation.docx_provider import HybridDocxEditController, ReplaceTextCommand, FieldKind


class RuntimeDocxTests(unittest.TestCase):
    def test_synthetic_docx_edit_and_reverse_plan(self):
        sample = Path(__file__).resolve().parents[1] / "samples" / "synthetic_dev3.docx"
        source = sample.read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            scope = Scope("synthetic-tenant", "synthetic-project")
            store = LocalDocumentLifecycleStore(Path(tmp) / "state")
            state = store.register(
                DocumentRecord("synthetic-doc", scope, "synthetic.docx", "DOCX", (), None, "", ""),
                initial_content=source,
            )
            controller = HybridDocxEditController(store, schema_trust_resolver=lambda *_: True)
            result = controller.execute(
                "synthetic-doc", scope,
                ReplaceTextCommand("ACME", "NOVA", 1, FieldKind.NON_MATERIAL_TEXT, change_summary="synthetic smoke"),
                expected_generation=state.generation,
            )
            self.assertEqual(result.code, "confirmed_success")
            controller.provider.plan(
                store.read_working("synthetic-doc", scope),
                ReplaceTextCommand("NOVA", "ACME", 1, FieldKind.NON_MATERIAL_TEXT),
                trusted_schema=True,
            )


if __name__ == "__main__":
    unittest.main()
