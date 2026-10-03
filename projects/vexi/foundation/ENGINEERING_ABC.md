# Vexi v0.1.5 — инженерный контракт A+B+C

Статус: DEVELOPMENT / PARTIAL INTEGRATION. Это проверяемая первая сборка foundation, а не замена всех возможностей Core v0.1.4 и не готовый релиз v0.1.5. Голосовой field test на ноутбуке, свободный разговор и надёжная адресованность продолжений остаются открытыми.

## Источники и приоритет

1. [Vexi v0.1.5 | Workspace, Documents & Context Foundation](https://app.notion.com/p/3daf50fc3b4d815c9233eae745adf1ff), редакция 2026-09-13 20:21 UTC: точный scope этого изменения.
2. [Agent Runtime Kernel v1.1](https://app.notion.com/p/3d9f50fc3b4d81789081f821ea4e82c9): typed routing, A0–A4, восемь truthful execution states, coherent replacements.
3. [Sensitive Data Lifecycle v1.0](https://app.notion.com/p/3cef50fc3b4d81f0b26dc98fb0779506): cumulative classes, purpose, scope, destinations, retention, no hidden copies.
4. [Stale-State Reconciler v1.1](https://app.notion.com/p/3cef50fc3b4d817bb64dcc0e39bf1102): invalidation after material events, history and affected IDs.
5. [Legal Source Hierarchy](https://app.notion.com/p/3ccf50fc3b4d811282cbd0b58db4e5f3): applicability/currentness before authority comparison.
6. [Expected Loss Controller v1.2](https://app.notion.com/p/3cef50fc3b4d81e4a9e1e42836925a6b): risk and execution priority are independent; UNKNOWN does not imply low risk or replace the user's objective.

Notion verification labels are unverified; selection is based on the explicitly named page and canonical ownership, not search rank or timestamp alone. The second similarly named planned v0.1.5 page is not the scope owner. Kernel's older recognized-text logging rule is narrowed by the explicit v0.1.5 ambient/privacy rule. No legal case data was imported into this generic implementation.

Input baseline: user-supplied `Vexi_v0.1.4_Public_Preview_Chrome.zip`; SHA-256 `0b86e358bc9779abc51f8d5d5066809c733a8b46648a315dde677d5e916fe96b`, matching published release metadata. Core identity: 0.1.4 / public-preview / media-context-natural-control. Original ZIP remains unchanged.

## A. Ownership and input boundary

`AttentionGate` owns permission to route an utterance. `TaskSession` owns the unresolved objective. `ConversationSession` owns turn-taking and TTS state. `ContextResolver` owns scoped, fresh target selection. None may grant capability authority.

The intake adapter creates an Actor and local attention signals. The model cannot choose Actor, SpeakerRole, continuation binding, verified owner, public target status, source authority or approval tokens. All these fields are trusted-runtime inputs, not model tool arguments.

Pipeline:

```text
microphone buffer in RAM -> local STT -> local address detection
  -> AttentionGate -> DROP (release text/audio, metadata only)
                   -> ACCEPT -> typed intent -> context -> policy
                             -> scoped provider -> readback -> response
```

`AttentionSignals(actor, addressed, ambient, continuation_bound, task_id)` contains no text. Result is `AttentionDecision(attention, accept, code)`. The gate deliberately cannot log a transcript it never receives.

AttentionClass is DIRECTED / CONTEXTUAL / AMBIENT / UNKNOWN. Priority: MUTED blocks all; known ambient overrides address hints; explicit addressing accepts; a bound continuation accepts only in the matching actor/task or valid conversation turn; everything else silently drops. Barge-in only stops TTS.

For actual acoustic input, a name mentioned in a conversation is still a possible false activation. The current wake detector is a candidate local heuristic, not proven speaker/address recognition. Acoustic precision requires a labelled field corpus.

## A. State machines

Task states: ACTIVE, AWAITING_INPUT, BLOCKED, SUSPENDED, COMPLETED, CANCELLED.

| Event | From | To | Guard/effect |
|---|---|---|---|
| Accepted new objective | none | ACTIVE | actor + tenant/project + opaque goal reference |
| Missing argument / user reports failure | ACTIVE | AWAITING_INPUT | preserve objective; clear contradicted evidence |
| Policy or source conflict | nonterminal | BLOCKED | record blocker reference; no speculative mutation |
| Wait / process restore | nonterminal | SUSPENDED | no execution, no retained authentication |
| Explicit resume / blocker resolved | nonterminal | ACTIVE | caller revalidates actor/scope and fresh state |
| Explicit completion | nonterminal | COMPLETED | clear target and expected-response context |
| Explicit cancellation | nonterminal | CANCELLED | clear context; never undo prior effects implicitly |
| Timeout / unrelated speech | any | unchanged | never completes or deletes a task |
| Any implicit reopening | terminal | rejected | a new objective gets a new task ID |

The TaskSession primitive exposes guarded transitions; the orchestration layer is responsible for validating resume/blocker-resolution events before calling transition. A failed action does not become the last verified target. One actor's turn does not erase another actor's task. The current bridge supports one unresolved task per actor; selecting among multiple tasks for one actor is an explicit future resolver extension.

Conversation states: INACTIVE, LISTENING, THINKING, EXECUTING, SPEAKING, MUTED, RECOVERY. Activation enters LISTENING. Speaking starts with no reply deadline; completing TTS starts the configurable reply window. Barge-in clears that deadline without accepting a turn. Muting drops audio and pending buffers. Recovery records only a safe code. Conversation closure does not implicitly complete the task unless explicitly requested.

THINKING and EXECUTING are declared for later model/tool UI integrations; the current voice bridge uses LISTENING/SPEAKING/MUTED/RECOVERY. Do not infer complete UI wiring from enum presence.

## A. Task/context contract and persistence

TaskSession fields: task_id, actor, scope, goal_ref, state, last_target_ref, expected_response_ref, recent_action_ref, verified_result, revision. Runtime context is volatile and separate from personal memory and model history.

Resolution order: fresh explicit target; fresh active app/document in scope; last verified task target if its observed version still matches. A stale explicit target raises `stale_target`; it never falls back to a different document. Cross-scope or cross-actor lookup raises `context_scope`. Missing target yields no result; ambiguous business references do not pick an arbitrary candidate.

`TaskStore.save/restore` is an opt-in atomic local metadata checkpoint. It stores opaque goal/task/scope references and terminal state, not transcripts, document contents, model history, approval tokens or verified target snapshots. Nonterminal restores are SUSPENDED. Corrupt or cross-scope checkpoints fail explicitly. The store requires an owner-protected non-synced directory and is not yet connected to default microphone sessions. Reference IDs themselves remain subject to retention policy.

Pending integration: goal decomposition, expected-response classifiers, fresh active-document observations and same-speaker binding. Current microphone input has no such binding evidence: an open task alone never authorizes wake-free speech. Trusted text/API adapters can supply a verified continuation; deterministic tests cover a task continuation after an arbitrarily long delay.

## B. Authority and capability policy

SpeakerRole: OWNER / GUEST / UNKNOWN. An Actor claiming OWNER is insufficient. OwnerAuthority stores an expiring binding of subject + session + tenant/project, installed only through a trusted local operator/authentication surface. Voice defaults UNKNOWN on every session; neither wake word nor «я владелец» promotes it.

Capability decisions: ALLOW, DENY, AWAITING_APPROVAL. Decision order: registered capability; release hard-deny; privacy route; fresh/non-conflicting state; resolved target/payload; guest-safe profile; verified owner; exact one-use owner approval; otherwise await owner. Provider entrypoints repeat binding and permission checks.

| Capability | Guest/unknown | Verified owner | Current implementation |
|---|---|---|---|
| General public conversation/question | PUBLIC-only route, no owner memory | same privacy gate | simple greeting/time/version; free-form model route pending |
| Play/pause, player volume, player fullscreen | allow public resolved media | allow | structured Browser Pack adapter, fresh readback |
| Public navigation / allowlisted app | only public safe target; app explicitly allowlisted | policy applies | contract only; no generic legacy fallback |
| Workspace read/create/mutate | deny until exact owner approval | scope + privacy + provider checks | exclusive TXT/MD draft create; other typed ops unsupported |
| Owner memory / business DB | owner-only or exact owner approval | scoped route required | not connected in candidate voice |
| Template learning / approval | exact separate owner decision | exact separate owner decision | policy only; no template provider |
| Communication / security / Legal-Finance / permanent deletion | DENY | DENY | disabled in this development release |

Risk classification is held in the registry: A0 read/public question; A1 reversible media; A2 approved launch/new local draft; A3 document/workflow mutation; A4 irreversible/financial/legal/security; UNKNOWN fail-closed. Registered capability does not mean a provider exists. Unsupported operations return UNSUPPORTED with no LLM action claim.

Approval binds operation ID, subject/session/role, scope, capability, target, payload SHA-256, expected version, all privacy fields and destination. TTL is bounded by owner session expiry. Every token is one-use, including invalid mismatched attempts; revoke owner invalidates outstanding grants. Learning approval cannot approve a later template promotion because capability/action/hash differ.

`foundation_console.py --owner-console` is an explicit trusted local OS-session operator surface with a 30-minute binding. It assumes the OS account and terminal are controlled by the owner; it is not biometric verification or protection against another person using an unlocked owner desktop. It grants no permissions to the microphone process. A dedicated reauthentication UI is still required for a stronger shared-device profile.

## B. Privacy lifecycle

DataClass is cumulative: PUBLIC, INTERNAL, CONFIDENTIAL, PERSONAL, SPECIAL_CATEGORY, RESTRICTED_CASE, SECRET. PrivacyContext includes purpose, allowed destinations, retention, deletion trigger, lawful basis status, redaction, encryption. Scope and actor reside in PermissionRequest. Missing/unresolved required fields block non-public routes.

This slice supports LOCAL_TOOL and LOCAL_STORAGE; LOCAL_MODEL is allowed by policy only for PUBLIC. No approved external processor registry exists, so external routes are denied. SECRET is denied by these general-purpose providers, including when combined with PUBLIC; credentials remain in the dedicated OS credential adapter, never in utterance/model payloads.

Ambient audio formerly written to temporary WAVs now stays in RAM. Ambient text is discarded before canonicalization, routing, overlay and model calls. Python buffer disposal is not a claim of forensic memory erasure; crash dumps/swap are an OS concern. TTS output fallback can still use a temporary WAV and removes it after playback; it is not microphone input retention.

Normal runtime telemetry permits a small set of metadata-only event templates. Legacy payload-bearing logs and exception reprs are suppressed by handler filters. This does not delete old v0.1.4 logs. No memory onboarding or owner-memory constructor is reachable from the candidate voice facade.

## C. Protocol, provider and document boundary

`WorkspacePolicy(workspace_id, scope, root)` is per business/project. No canonical hardcoded folder tree. `WorkspaceProtocol.execute(DocumentCommand, now, approval) -> Result` is shared Python protocol; higher-level agents may provide Local or Business Gateway adapters. PostgreSQL remains future business structured truth; local files are artifacts, not silent replacements for DB facts.

WorkspaceOperation: CREATE, SEARCH, LIST, COPY, MOVE, RENAME, TRASH, ARCHIVE, METADATA, WATCH. Enum coverage is protocol coverage only. LocalDraftWorkspace implements exclusive new TXT/MD draft creation as the smallest real disk proof; it returns UNSUPPORTED for all other operations. DOCX/PDF/Office providers belong to the subsequent work packages.

DocumentCommand carries PermissionRequest + operation + workspace-relative path + content bytes. PermissionRequest binds immutable intent to actor/scope, payload hash and expected version. CREATE requires expected_version=ABSENT. It cannot overwrite or silently create an automatic numeric suffix on collision. Result requires readback evidence before CONFIRMED_SUCCESS.

Paths reject traversal, absolute/UNC/drive paths, alternate streams, device names, ambiguous Windows trailing dots/spaces, symlinks and reparse points. Parent directories must already exist. Exclusive create prevents overwrite races. The Python path checks are not an atomic security boundary against a hostile process swapping ancestor directories; such roots are unsupported until a Windows handle-relative/no-reparse provider is implemented.

Minimal DocumentRecord: document_id, scope, relative_path, document_type, linked object_refs, canonical_version, working_revision, content_hash, lifecycle, stale. This is the C-level identity/resolution subset. Full language/jurisdiction, template/version, source snapshots, approvals, outputs, privacy/retention/provenance live on the later Document Object Model; no completeness claim for E–O modules.

WorkspaceResolver selects only indexed objects in scope, of the requested type and linked business object. Zero -> NOT_FOUND; multiple -> AMBIGUOUS; missing canonical or stale -> blocked resolution. Natural «last invoice»/date references require canonical indexing and are not emulated by global disk fuzzy search.

## Shared change detection and source reconciliation

Materiality: IDENTICAL / COSMETIC / CONTENT / BUSINESS_MATERIAL / HIGH_RISK / UNKNOWN. Equal raw hashes are identical. Different hashes alone never prove semantic/business change. A provider must supply structural/semantic classification with evidence; no such DOCX classifier exists in this slice.

DependencyGraph is instantiated per authorized scope. It computes a cycle-safe transitive affected-ID set, preserves prior change events and marks source/dependents stale. Cosmetic changes record history without invalidation. UNKNOWN means pending review with stale gating. No external change auto-promotes to canonical truth. Graph persistence, raw revision storage and automatic policy linkage are later work, not represented as complete here.

Configurable SourceHierarchy defaults to CANONICAL_DB > VERIFIED_INTEGRATION > APPROVED_DOCUMENT > PARSED_FILE > USER_STATEMENT > MODEL_INFERENCE. Scope, applicability, verification time and stale-after are filtered before ranking. Conflicting value references produce an explicit SourceResolution.conflict tuple; preferred is only a candidate. Write orchestration must carry conflict/stale flags into PermissionRequest. Cosmetic/semantic classification and source resolution cannot be supplied by an untrusted model as authoritative facts.

## Truth and failure contract

Result states: CONFIRMED_SUCCESS, SENT_NOT_CONFIRMED, ALREADY_SATISFIED, NOT_FOUND, BLOCKED, UNSUPPORTED, FAILED, AMBIGUOUS. Success-like states require Evidence(operation_id, target_id, observed_hash, check). An ACK alone never proves success. Policy AWAITING_APPROVAL maps to execution BLOCKED with a distinct reason; no mutation has happened.

Media commands read the current public YouTube target twice before dispatch, and verify the requested property on the same URL after dispatch. Fullscreen OFF uses an explicit false property value. Browser Protocol v1 lacks atomic expected-tab/version binding: a tab switch between last read and command is an unresolved field/race gate. No guest fallback to unscoped hotkeys is used.

## Actual integration with 0.1.4

The verified public Core sources are kept in `core/`. Its entrypoint now uses `attention_loop.run_voice_loop` and FoundationBridge. Legacy Router/adapters remain available as reference source for subsequent typed migration but are not reachable through the new voice facade. This intentionally limits the development candidate; it must not replace the everyday v0.1.4 installation as a feature-complete upgrade.

The old v0.1.4 regression checks remain and run alongside behavioural tests. Their router-route checks are source-string checks and are not evidence that all old capabilities work through the new facade.

## Regression and release gates

Automated suites cover ambient DROP with spies on Router/TTS/canonicalizer, task survival, actor changes, scope, explicit close, barge-in, expired/replayed/altered approvals, owner spoofing, high-risk denies, cumulative SECRET, stale/conflict gates, traversal, no overwrite, readback, source conflict, duplicate/cosmetic/material changes, cycle-safe graph and metadata checkpoint recovery. Media integration uses a synthetic Browser Pack, labelled as such.

Release discipline:

```text
verify input ZIP hash -> preserve baseline -> stage whole modules
 -> syntax + deterministic regression -> launch local text process
 -> synthetic disk/readback exercise -> rollback -> verify baseline hashes
 -> notebook voice/Browser Pack/ambient field matrix -> promote or reject
```

The rehearsal works inside a new isolated directory; no running install, startup registration, user memory, real document or Chrome profile is replaced. The development ZIP excludes the old public installer, logs/config secrets, caches and model binaries.

Promotion stays blocked until: bound wake-free voice continuation; safe free-form conversation; owner reauthentication UX; desired legacy routes migrated behind typed policy; real notebook launch/microphone/barge-in; current-tab race enforcement; real document providers/versions/recovery; scoped retained-data lifecycle; complete representative local field tests. Test-green foundation does not imply release-ready Vexi.
