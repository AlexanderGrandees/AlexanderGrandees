# Vexi 0.1.5.dev3 - Headless DOCX + Hybrid Approval

Status: DEVELOPMENT MODULE / NOT A LIVE UPDATE.

## Decision
Hybrid document mutation policy is canonical for this slice:

- small reversible changes may execute automatically only when the field is resolved by a trusted schema/template source;
- every applied change first ensures an immutable recovery checkpoint;
- business-material, high-risk, general/unknown or untrusted-schema changes require explicit owner confirmation;
- canonical promotion remains a separate operation and is never implied by a successful edit.

The model cannot authorize `trusted_schema`. `HybridDocxEditController` obtains trust from an injected trusted `schema_trust_resolver`. Owner confirmation is checked through an injected approval verifier and bound to document identity, scope, generation and the exact edit plan fingerprint.

## Implemented provider scope

- headless DOCX processing with Python standard library Open XML/ZIP primitives;
- exact replacement in main document, headers and footers;
- text split across multiple Word runs is resolved as one paragraph string;
- table-cell paragraphs are supported because they are part of the main story XML;
- exact expected-occurrence contract: mismatch blocks, no fuzzy/regex fallback;
- post-write re-open/readback verification using paragraph hashes;
- non-target ZIP members are preserved;
- no Microsoft Word installation required.

## Safety gates

- package/member/uncompressed/XML size limits;
- compression-ratio guard;
- duplicate ZIP member rejection;
- path traversal/unsafe ZIP member rejection;
- encrypted member rejection;
- macro-enabled package rejection;
- digitally signed package rejection because editing would invalidate the signature;
- DTD/entity XML rejection;
- tracked-changes story rejection for this release;
- Word field-code paragraph rejection when it is the edit target;
- stale document and generation mismatch fail closed.

## Recovery semantics

The controller creates or reuses an immutable version of the pre-edit working bytes before mutation. The new bytes are then persisted as a working revision and re-opened. If verification fails after persistence, the controller attempts an automatic restore from the recovery version and reports failure rather than success. Material/approved results also receive a post-edit immutable checkpoint. Low-risk automatic edits remain working revisions, avoiding unnecessary formal-version spam while preserving the pre-edit recovery point.

## Deferred

- section insertion/removal;
- table row insertion/removal;
- image/logo replacement;
- comments/footnotes/endnotes/text-box editing;
- tracked-change aware editing;
- Word field update semantics;
- workspace-file export/sync and atomic file replacement;
- Live Word/Excel concurrent-edit binding;
- Template Registry implementation that supplies the trusted schema resolver;
- production installer/migration.

## Evidence

Local reconstructed dev2+dev3 harness: 43/43 deterministic tests PASS on 2026-09-13.

This is not the full dev1 A+B+C regression. Exact dev1 interface hashes are encoded in the target validator; full A+B+C plus dev2+dev3 regression and Windows synthetic field testing remain promotion gates.
