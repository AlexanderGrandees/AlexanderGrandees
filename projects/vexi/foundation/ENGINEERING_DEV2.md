# Vexi 0.1.5.dev2 - Document Identity, Autosave, Versioning & Recovery

Status: DEVELOPMENT MODULE / NOT A LIVE UPDATE.

## Goal

Close the document-lifecycle gap before DOCX and Live Office providers are allowed to mutate real documents. dev2 establishes identity, immutable content storage, working revisions, material checkpoints, explicit canonical promotion, safe rollback and corruption detection.

## Scope

Implemented in `core/vexi_foundation/document_lifecycle.py`:

- `DocumentState` with monotonic `generation`.
- `WorkingRevision` for autosave/recovery without formal version spam.
- immutable `DocumentVersion` checkpoints.
- scope-isolated content-addressed SHA-256 local blob store; no cross-tenant/project blob deduplication.
- checksum-protected metadata envelope.
- atomic metadata replacement (`os.replace`).
- per-document exclusive cooperative lock.
- optimistic `expected_generation` conflict detection.
- explicit canonical promotion with `expected_canonical` compare-and-set and current-working-checkpoint binding.
- rollback as a new working revision, never silent history rewrite.
- stale marker and lifecycle state transitions.
- immutable blob readback verification.
- explicit stale-lock recovery; never auto-delete a lock.
- orphan blob discovery after crash/interrupted transactions.
- metadata-only audit events. No document body is copied into audit metadata.

## Invariants

1. Autosave does not automatically create a formal version.
2. Cosmetic checkpoints do not create formal versions.
3. CONTENT / BUSINESS_MATERIAL / HIGH_RISK / UNKNOWN checkpoints preserve an immutable version.
4. A checkpoint is not canonical automatically.
5. Canonical promotion is a separate caller-authorized operation.
6. Rollback does not erase or rewrite history; it restores an old version as a new working revision.
7. `APPROVED`/`ACTIVE` require a non-stale canonical version.
8. Tenant/project scope gets separate metadata, locks and blob namespaces; the same document ID may safely exist in different scopes.
9. Wrong-scope lookup returns not-found semantics instead of revealing another scope's identity.
10. Scope mismatch, generation mismatch, corrupt metadata or corrupt/missing blobs fail closed.
11. Blob write before metadata commit can leave only an orphan blob; it cannot silently become document truth.
12. A stale document cannot be made fresh by re-promoting the same canonical version; explicit revalidation/new checkpoint is required.
13. Provider-specific DOCX/PDF semantics remain outside this module.

## Security boundary

This store assumes its root is local, owner-controlled and not writable by a hostile local process. The cooperative lock is not an OS sandbox and does not defeat an attacker with filesystem access. Policy/approval is deliberately outside the store: mutating callers must already have passed the Vexi capability/privacy gate.

No SECRET/external routing is added. No Notion/Telegram/LLM document sink is added.

## Why this comes before DOCX

A DOCX provider without version identity/recovery can produce edits that the assistant cannot prove, rollback or distinguish from concurrent/manual changes. dev2 gives providers a deterministic state contract first. The next package can therefore implement headless DOCX against explicit `expected_generation`, current canonical version and verified readback rather than ad-hoc file mutation.

## Promotion gate for this module

Required before merging into a wider candidate:

- all dev1 A+B+C regressions remain green in the full source tree;
- dev2 tests green;
- Windows/Python 3.11 local run;
- simulated crash/orphan behavior observed;
- lock recovery observed;
- no real user document used in first field test;
- then headless DOCX provider can begin.
