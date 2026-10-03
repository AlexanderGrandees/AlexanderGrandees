"""Synthetic-only smoke test. Run only inside an isolated dev1+dev2+dev3 source tree."""
from pathlib import Path
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core" if (ROOT / "core").is_dir() else ROOT))
from vexi_foundation.contracts import Scope
from vexi_foundation.workspace import DocumentRecord
from vexi_foundation.document_lifecycle import LocalDocumentLifecycleStore
from vexi_foundation.docx_provider import HybridDocxEditController, ReplaceTextCommand, FieldKind

sample = Path(__file__).resolve().parent / "samples" / "synthetic_dev3.docx"
source = sample.read_bytes()
with tempfile.TemporaryDirectory() as tmp:
    scope = Scope("synthetic-tenant", "synthetic-project")
    store = LocalDocumentLifecycleStore(Path(tmp) / "state")
    state = store.register(DocumentRecord("synthetic-doc", scope, "synthetic.docx", "DOCX", (), None, "", ""), initial_content=source)
    controller = HybridDocxEditController(store, schema_trust_resolver=lambda *_: True)
    result = controller.execute("synthetic-doc", scope,
        ReplaceTextCommand("ACME", "NOVA", 1, FieldKind.NON_MATERIAL_TEXT, change_summary="synthetic smoke"),
        expected_generation=state.generation)
    if result.code != "confirmed_success":
        raise SystemExit("SMOKE FAILED: " + result.code)
    # Reverse planning proves the resulting package is structurally readable and contains NOVA once.
    controller.provider.plan(store.read_working("synthetic-doc", scope),
        ReplaceTextCommand("NOVA", "ACME", 1, FieldKind.NON_MATERIAL_TEXT), trusted_schema=True)
    print("DEV3 SYNTHETIC SMOKE PASS")
