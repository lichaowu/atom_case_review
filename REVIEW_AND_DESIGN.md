> **Status (as of 2026-05-21): HISTORICAL DESIGN RECORD.**
>
> This document is the original design proposal that preceded implementation.
> All §8 decisions were approved as proposed (✅ for items 1–5), and the plugin
> shipped at `atom-mvp v0.7.4-phase6a` (2026-05-19). Counts cited below
> (98 atoms, 874 claims) reflect the Bitable state on 2026-05-15 before the
> v2.1 NSA ingest; current totals are 175 atoms / 1,260 NSA-active rules
> (see `PROJECT_NOTES.md § 2`). The payload schema discussed in §3.7 was
> superseded by v0.6 in Phase 5; see `docs/payload-schema.md` for the current
> contract. **For current state, refer to `PROJECT_NOTES.md` and
> `CHANGELOG.md`. This file is preserved for posterity.**

---

# Case Review Atom MVP — Review & Design

> Sibling plugin to `case_review_mvp/` tailored for the **ATLAS Atom Rules** model
> (Bitable `LGf7bfNwla5QmcscMEhljFWjgId`, tables `tblUnjW7W9hiAJ93` Atoms +
> `tblWrb1MWg7nzV3d` Atom Rules). Current plugin is **NOT modified**.
>
> Status: design proposal, awaiting sign-off on §8 decisions before implementation.

---

## 0. TL;DR

> **Scope note (V0.1, locked):** this plugin uses **only the ATLAS Atom Rules**
> (`tblWrb1MWg7nzV3d`) and **ATLAS Atoms** (`tblUnjW7W9hiAJ93`). The legacy V0.3
> Rule Book (`tblpb9iv2DUm8nRO`) is **NOT** loaded, retrieved, scored, or
> referenced anywhere in this plugin. The two consoles are fully decoupled.

The current `case_review_mvp` plugin is built around the **V0.3 collapsed-tier rulebook**
(L0/L1/L2/L3 nodes, FLAG/PASS verdict, BM25 retrieval over text fields). The new
**ATLAS Atom Rules** schema is a fundamentally different data model: a **claim engine**
where each rule is a Boolean gate over typed atoms (C/S/P/R/E + M/X) and emits a
4-way outcome (`VIOLATION` / `NOT_RECOMMEND` / `NOT_FOR_FEED` / `APPROVE`) with
modifier/exception lifts.

| Dimension                | Current `case_review_mvp`                       | New `case_review_atom_mvp`                                  |
|--------------------------|-------------------------------------------------|-------------------------------------------------------------|
| Rule model               | L0/L1/L2/L3 collapsed-tier nodes                | Atom claim gates (DNF / legacy AND-list)                    |
| Verdict                  | binary FLAG / PASS                              | 4-way outcome + lifts (incl. routing pointer)               |
| Case-row signals         | text fields only                                | text fields + 7 atom-link DuplexLink fields                 |
| Retrieval                | BM25 over text                                  | BM25 + atom-overlap (weighted Jaccard mix)                  |
| Specialist               | `nsa-precedent-review` (text reasoning)         | `nsa-atom-precedent-review` (engine-validated)              |
| Bitable tables           | Rule Book, Case Notes, Pending Cases            | ATLAS Atoms + ATLAS Atom Rules + Case Notes + Pending Cases |
| Payload schema           | `case-review-payload` v0.4                      | `case-review-atom-payload` v0.1                             |

**Recommendation:** ship as a **sibling plugin** under `case_review_atom_mvp/` so the
existing console keeps working unchanged for V0.3 reviewers while the new console
serves atom-rule reviewers. Both consoles share the same Bitable.

**Reuse estimate:** ~55% of files copy verbatim, ~20% modified, ~25% new.

---

## 1. ATLAS Data Model (verified against Bitable)

### 1.1 Atoms table — `tblUnjW7W9hiAJ93`
- **98 atoms** across 7 dimensions: **C**ontent (44), **S**ubject (4), **P**ortrayal (11),
  **R**ealism (5), **E**xplicitness (2), **M**odifier (26), e**X**ception (6).
- Key fields: `serial_code`, `atom_name`, `atom_key` (the canonical ID, e.g.
  `C1`, `S2`, `M5`, `X4`), `dimension`, `description`, `audit_rule`, `tax_version`.
- 12 DuplexLink fields connect atoms to Case Notes (7 — one per dimension) and
  to Atom Rules (5+ — one per dimension that participates in gates).

### 1.2 Atom Rules table — `tblWrb1MWg7nzV3d`
- **874 claims** (sample shows distribution across 17 NSA titles; top: ASL 64,
  ASB 60, LBE 54, AN 53, YNSN 53).
- Outcomes (first 500 sampled): **APPROVE 458, VIOLATION 19, NOT_RECOMMEND 19,
  NOT_FOR_FEED 4** — heavy APPROVE skew because most claims are exception/lift
  branches that approve when context fires.
- Gate shape: per-dimension multi-select link fields
  (`content_atoms`, `subject_atoms`, `portrayal_atoms`, `realism_atoms`,
  `explicitness_atoms`) — **AND across dimensions, OR within a dimension**.
- Lifts:
  - `modifiers_required` / `modifiers_excluded` — hard preconditions
  - `modifiers_lift_to_approve` + `modifiers_lift_to_json` (DNF: list of AND-groups)
  - `exceptions_required` / `exceptions_lift_to_approve`
  - `exception_qualifiers_json` + `exception_qualifier_modifiers_json` (legacy
    AND-list shape — qualifier atoms must accompany the exception)
- Routing pointers (metadata only, do not change verdict): `non_realistic_routes_to`,
  `cross_title_redirect`.

### 1.3 Case Notes table — `tblhB50JyhKR3Ojf`
- 27 fields including 7 atom-link DuplexLinks
  (`content_atoms`, `subject_atoms`, `portrayal_atoms`, `realism_atoms`,
  `explicitness_atoms`, `modifier_atoms`, `exception_atoms`).
- This is the bridge: a Case Note is a precedent **already tagged with atoms**.

### 1.4 Decision-path semantics (from sampled claim AN.001)
1. Resolve case atoms across all 7 dimensions.
2. For each candidate claim, evaluate gate: `∀d ∈ {C,S,P,R,E}: case.d ∩ claim.d ≠ ∅`
   (skip dimensions the claim leaves empty).
3. If `requires_exception_context` is set, gate also requires the exception fired.
4. On gate-hit, base outcome = `outcome` field.
5. Apply modifier/exception lifts in order:
   - if any modifier in `modifiers_excluded` is present → claim suppressed
   - if every group in `modifiers_required` matches → keep going
   - if any group in `modifiers_lift_to_json` matches → lift to APPROVE
   - if `exceptions_lift_to_approve` and one of `exceptions_required` is in
     case.X **and** its qualifier list (from `exception_qualifiers_json`) matches
     case atoms **and** any required qualifier modifiers match → lift to APPROVE
6. Severity sort across all gate-hit claims:
   `VIOLATION > NOT_RECOMMEND > NOT_FOR_FEED > APPROVE`. Tie-break by
   `len(content_atoms ∪ subject_atoms ∪ portrayal_atoms)` descending (most
   specific gate wins) then `claim_id` ascending for stability.
7. Routing pointers attached as metadata; do not override severity.

---

## 2. Why the current plugin doesn't fit

| Surface                | Current behavior                               | Atom-rule need                                      | Verdict |
|------------------------|------------------------------------------------|-----------------------------------------------------|---------|
| Loader                 | Reads Rule Book + Case Notes + Pending only    | Loads Atoms + Atom Rules + Case Notes + Pending (no Rule Book) | rebuild |
| Case row UI            | Text fields                                    | + 7 atom chip rows, optional auto-tagger            | rebuild |
| Retriever              | BM25 over text                                 | BM25 ⊕ weighted atom-overlap                        | extend  |
| Engine                 | None — specialist freelances verdict           | Deterministic claim engine before specialist        | new     |
| Payload                | `case-review-payload` v0.4                     | `case-review-atom-payload` v0.1                     | new     |
| Specialist             | `nsa-precedent-review`                         | `nsa-atom-precedent-review` (engine-validated)      | new     |
| Verdict UI             | FLAG/PASS + applied_rule_chain                 | 4-way outcome + applied_claim_chain + lifts trail   | rebuild |

`grep -i "atom\|ATLAS" plugin/dist/index.html` returns **0 hits** — confirming
zero awareness of the new schema in the current console.

---

## 3. New Plugin Architecture — `case_review_atom_mvp/`

### 3.1 Layout
```
case_review_atom_mvp/
├── REVIEW_AND_DESIGN.md       (this file)
├── plugin/
│   ├── dist/index.html        (single-file React-no-JSX, Bitable extension)
│   └── manifest.json
├── skills/
│   └── nsa-atom-precedent-review/
│       ├── SKILL.md
│       └── schema/atom-verdict.schema.json
└── docs/
    ├── payload-schema.md
    └── engine-spec.md
```

### 3.2 Architecture diagram
```
Bitable ─┐
         ├─► Loader ─► {atoms, claims, cases, pending}
         │                       │
         │                       ▼
         │             ┌─► AtomTagger UI ◄─ optional auto-tag
         │             │           │
Reviewer ┤             ▼           ▼
         │       Retriever (BM25 + Jaccard) ─► top-K precedents
         │                       │
         │                       ▼
         │       DeterministicEngine ─► gate hits + lifts + severity
         │                       │
         │                       ▼
         └─► Payload v0.1 ─► nsa-atom-precedent-review ─► verdict JSON
                                                              │
                                                              ▼
                                                       Verdict UI
```

### 3.3 Loader changes
- Constants (Rule Book intentionally absent):
  ```
  ATOMS_NAMES   = ["ATLAS Atoms", "Atoms"]
  CLAIMS_NAMES  = ["ATLAS Atom Rules", "Atom Rules"]
  CASES_NAMES   = ["Case Notes"]            // precedent corpus, atom-tagged
  PENDING_NAMES = ["Pending Cases"]
  // RULES_NAMES from the V0.3 plugin is NOT carried over.
  ```
- Atom record shape:
  ```
  { atom_key, atom_name, dimension, description, audit_rule, serial_code }
  ```
- Claim record shape (DuplexLinks resolved to `atom_key[]`):
  ```
  {
    claim_id, policy_titles[], issue, outcome, status, tax_version,
    gates: { C[], S[], P[], R[], E[] },
    modifiers_required: AndGroup[],   // legacy AND-list
    modifiers_excluded: string[],
    modifiers_lift_dnf: AndGroup[],   // DNF
    exceptions_required: string[],
    exception_qualifiers: { [xKey]: AndGroup[] },
    exception_qualifier_modifiers: { [xKey]: AndGroup[] },
    requires_exception_context: bool,
    exceptions_lift_to_approve: bool,
    routing: { non_realistic_routes_to, cross_title_redirect },
    notes
  }
  ```
- Case-row atoms: resolve 7 DuplexLink fields → `caseAtoms = {C[], S[], P[], R[], E[], M[], X[]}`.

### 3.4 AtomTagger UI
- 7 horizontal rows, one per dimension; each row is a chip multi-select with
  search-as-you-type filter over `atom_key`/`atom_name`/`description`.
- Optional **Auto-tag** button → runs `atlas-atom-tagger` skill on
  `{visual_summary, asr_text, ocr_text, caption_text}` and pre-fills chips
  (reviewer must explicitly accept).
- Auto-tagging **OFF by default** to keep human-in-the-loop semantics for V0.1.

### 3.5 DeterministicEngine pseudocode
```js
function evalGate(claim, caseAtoms) {
  for (const d of ["C","S","P","R","E"]) {
    const need = claim.gates[d];
    if (need.length === 0) continue;
    const got = caseAtoms[d];
    if (!need.some(a => got.includes(a))) return false;
  }
  return true;
}

function applyLifts(claim, caseAtoms) {
  const M = caseAtoms.M, X = caseAtoms.X;
  if (claim.modifiers_excluded.some(m => M.includes(m))) return { suppress: true };
  if (claim.modifiers_required.length &&
      !claim.modifiers_required.every(group => group.every(m => M.includes(m))))
    return { suppress: true };

  const lifted = claim.modifiers_lift_dnf.some(group => group.every(m => M.includes(m)));
  if (lifted) return { outcome: "APPROVE", lift: "modifier" };

  if (claim.exceptions_lift_to_approve) {
    for (const x of claim.exceptions_required) {
      if (!X.includes(x)) continue;
      const qGroups = claim.exception_qualifiers[x] || [[]];
      const qModGroups = claim.exception_qualifier_modifiers[x] || [[]];
      const qOk = qGroups.some(g => g.every(a => allAtoms(caseAtoms).includes(a)));
      const mOk = qModGroups.some(g => g.every(m => M.includes(m)));
      if (qOk && mOk) return { outcome: "APPROVE", lift: `exception:${x}` };
    }
  }
  return { outcome: claim.outcome, lift: null };
}

const SEVERITY = { VIOLATION: 4, NOT_RECOMMEND: 3, NOT_FOR_FEED: 2, APPROVE: 1 };
function severitySort(hits) {
  return hits.sort((a,b) =>
    SEVERITY[b.outcome]-SEVERITY[a.outcome] ||
    b.specificity - a.specificity ||
    a.claim_id.localeCompare(b.claim_id));
}
```

### 3.6 Retriever
- BM25 over `visual_summary, topic, caption, asr, ocr, rationale` (existing
  weights kept) → `score_text`.
- Atom-overlap = weighted Jaccard between case atoms and precedent atoms,
  weights `{C:2.0, S:1.5, P:1.5, R:1.0, E:1.0, M:0.5, X:0.5}` → `score_atom`.
- Final: `score = 0.6 * normalize(score_text) + 0.4 * normalize(score_atom)`.
- Top-K = 5 by default (configurable).

### 3.7 Payload `case-review-atom-payload` v0.1
```json
{
  "schema": "case-review-atom-payload",
  "version": "v0.1",
  "issue": "NSA",
  "policy_title": "AN",
  "candidate": {
    "id": "pending_xxx",
    "visual_summary": "...",
    "asr_text": "...",
    "ocr_text": "...",
    "caption_text": "...",
    "atoms": { "C": ["C1"], "S": ["S1"], "P": ["P11"], "R": ["R1"], "E": [], "M": ["M5"], "X": [] }
  },
  "engine_result": {
    "gate_hits": [
      { "claim_id": "AN.001", "outcome": "VIOLATION", "lift": null,
        "specificity": 4, "evidence": { "C": ["C1"], "S": ["S1"], "P": ["P11"], "R": ["R1"] } }
    ],
    "applied_claim_chain": ["AN.001"],
    "verdict": "VIOLATION",
    "routing": { "non_realistic_routes_to": null, "cross_title_redirect": null }
  },
  "precedents": [
    { "id": "case_xxx", "score": 0.82, "score_text": 0.71, "score_atom": 0.94,
      "atoms": {...}, "outcome": "VIOLATION", "rationale": "...", "snippet": "..." }
  ],
  "candidate_claim": { "claim_id": "AN.001", "outcome": "VIOLATION", "...": "..." }
}
```

### 3.8 Specialist `nsa-atom-precedent-review`
- Input: `case-review-atom-payload` v0.1.
- Job: **validate** the engine result (do not re-derive), then add reviewer-facing
  rationale anchored to precedents.
- Output schema `atom-verdict`:
  ```json
  {
    "verdict": "VIOLATION",
    "confidence": 0.86,
    "applied_claim_chain": ["AN.001"],
    "lifts_applied": [],
    "rationale": "Case atoms {C1,S1,P11,R1} match AN.001 gate; no modifiers in M5 trigger lift_to_approve; precedents case_aaa, case_bbb show same outcome.",
    "agreements": ["case_aaa", "case_bbb"],
    "disagreements": [],
    "routing_notes": null,
    "engine_validated": true
  }
  ```
- Convention follows `specialist_output_convention.md` verbatim (single fenced
  ```json block, no prose outside).

### 3.9 Reuse map
| File / Module                         | Reuse                |
|---------------------------------------|----------------------|
| Bitable bootstrap, table discovery    | verbatim             |
| BM25 implementation                   | verbatim             |
| Field-weight constants for text       | verbatim             |
| `specialist_output_convention.md`     | verbatim             |
| Verdict UI shell (panes, layout, CSS) | modified (4-way)     |
| Retriever                             | extended (+ Jaccard) |
| Payload builder                       | modified             |
| Loader                                | modified (+2 tables) |
| AtomTagger UI                         | new                  |
| DeterministicEngine                   | new                  |
| Specialist skill + schema             | new                  |

---

## 4. Migration & coexistence
- Both plugins live in the same Bitable; reviewers pick the console matching
  the rulebook they want.
- **No breaking changes** to current `case_review_mvp/`.
- Optional, non-blocking: add a small banner in current plugin: *"For atom-rule
  cases, switch to Atom Console →"* (deferred to V0.2).

---

## 5. Invariants (per AIPRB §A5.2 Phase F)
1. Engine result is **deterministic** given `(caseAtoms, claims)`.
2. Specialist may dissent but must say so explicitly in `disagreements[]`;
   default is to validate and pass through.
3. Routing pointers never change verdict — metadata only.
4. Severity ordering: `VIOLATION > NOT_RECOMMEND > NOT_FOR_FEED > APPROVE`.
5. Empty gate dimension = wildcard for that dimension.
6. Modifier excluded > modifier required > modifier lift > exception lift.

---

## 6. Open questions
1. Tie-break for equal-severity multi-claim hits beyond specificity + claim_id?
2. Should `cross_title_redirect` surface as a reviewer prompt before final verdict?
3. Auto-tagger threshold for chip pre-fill confidence?
4. How to handle claims with `status != "active"`? (proposal: filter at load time)
5. Multi-issue cases (NSA + HRA) — out of scope for V0.1, NSA only.
6. Persisting reviewer-edited atom tags back to Case Notes — V0.2.

---

## 7. Effort estimate (~7 working days, 7 phases)
1. Scaffold sibling plugin + loader for Atoms + Atom Rules — 1 d
2. AtomTagger UI (no auto-tag) — 1 d
3. DeterministicEngine + tests against sample claims — 1.5 d
4. Retriever extension (atom-overlap mix) — 0.5 d
5. Payload v0.1 + Verdict UI 4-way — 1 d
6. Specialist skill `nsa-atom-precedent-review` + schema — 1 d
7. End-to-end QA against ≥10 precedents per outcome — 1 d

---

## 8. Decisions needed before implementation
1. **Plugin name:** `case_review_atom_mvp/` ✅?
2. **Skill name:** `nsa-atom-precedent-review` ✅?
3. **Scope V0.1:** NSA only; HRA / VBDA / HHB / SGC deferred ✅?
4. **Auto-tagging:** OFF by default, reviewer must opt in per case ✅?
5. **Banner** in current plugin pointing to atom console — defer to V0.2 ✅?

Reply with ✅ / ❌ / amendments per item, and I'll proceed to implementation.
