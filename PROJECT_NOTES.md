# case_review_atom_mvp — Project Notes

Working notes for the ATLAS Atom Rules Bitable plugin (NSA + HHB + HRA scope).
Companion to `CHANGELOG.md` (changes-by-version) — this doc is the **current-state snapshot**.

Last updated: **2026-06-04**, build `atlas-validator v0.18.0`.

---

## 1. What this is

A single-file React-CDN Bitable plugin that lets a T&S reviewer:

1. **Pick a pending case** from the `Pending Cases` table (issue-scoped dropdown)
2. **Tag it across 7 ATLAS atom dimensions** (C/S/P/R/E/M/X) using the AtomTagger UI
3. **Retrieve precedents** via dual-channel similarity (BM25 keyword + atom-Jaccard)
4. **Build a `case-review-payload v0.7`** with route-hint to the correct skill (NSA, HHB, or HRA)
5. **Paste back the skill's reasoned verdict JSON** into the ReasonedVerdictPane and view a structured render with proposed atoms, simulated claim chain, engine alignment, precedent analysis, watch-outs
6. **Confirm & save** the reviewed case to the Precedents table, with decision/policy override tracking for discrepancy analysis, and automatic status update of the pending case

Phase 7 (verdict-to-action loop) is now partially implemented — write-back to Precedents is live.

---

## 2. Current build artifacts

### Plugin
- **Path (in repo):** `plugin/dist/index.html`
- **Version constant:** `PLUGIN_VERSION = "atom-mvp v0.18.0-defensibility"`
- **Manifest version:** `0.18.0`
- **Size:** ~224 KB

### Skills
**NSA skill:**
- **Path (in repo):** `skills/nsa-atom-precedent-review/SKILL.md`
- **Skill key:** `nsa-atom-precedent-review` (live in marketplace as `mira-user-skills:nsa-atom-precedent-review`)
- **Version line:** `# NSA Atom Precedent Review (v1.7 — defensibility-consolidation)`
- **Appendix A:** atoms_catalog (76 atoms, ~23 KB inlined)
- **Appendix B:** non-approve claims (223 claims, ~52 KB inlined)
- **Verdict schema:** `skills/nsa-atom-precedent-review/schema/atom-verdict.schema.json`

**HHB skill:**
- **Path (in repo):** `skills/hhb-atom-precedent-review/SKILL.md`
- **Skill key:** `hhb-atom-precedent-review` (live in marketplace as `mira-user-skills:hhb-atom-precedent-review`)
- **Version line:** `# HHB Atom Precedent Review (v1.3 — defensibility-consolidation)`
- **Appendix A:** atoms_catalog (94 atoms, ~37 KB inlined)
- **Appendix B:** non-approve claims (109 claims, ~28 KB inlined)
- **Covers:** HSS (Hate Speech & Hateful Ideologies, Slurs) + BPI (Bullying, Personal Information)

**HRA skill:**
- **Path (in repo):** `skills/hra-atom-precedent-review/SKILL.md`
- **Skill key:** `hra-atom-precedent-review` (live in marketplace as `mira-user-skills:hra-atom-precedent-review`)
- **Version line:** `# HRA Atom Precedent Review (v1.3 — defensibility-consolidation)`
- **Appendix A:** atoms_catalog (118 atoms, ~33 KB inlined; C:66 / S:3 / P:13 / R:5 / E:2 / M:23 / X:6)
- **Appendix B:** non-approve claims (252 claims, ~78 KB inlined, 8 bundles EL1–EL6 + MX1–MX2)
- **Covers:** HRA (High Risk Activities — regulated goods, drugs, gambling, weapons, dangerous acts, frauds)
- **Outcome split:** VIO 218 / NFF 20 / NR 14 across 13 policy titles
- **SKILL.md size:** 142,808 bytes (1,281 lines)

### Bitable (AI Policy Rule Book)
- **Base token:** `LGbiYXGEFaPaXvsYU6ElSYe6gsc`
- ATLAS Atoms table: `tblUnjW7W9hiAJ93`
- ATLAS Atom Rules table: `tblWrb1MWg7nzV3d`
- ATLAS Molecules table: `tblhpm2SOraBjxJF`
- Precedents table: configured via `casesTableNames: ["Precedents"]`
- Pending Cases table: configured via `pendingTableNames: ["Pending Cases"]`
- Issue scope: **NSA + HHB + HRA** (HSS + BPI under HHB)

### Bitable (LIVE — Streaming Feature)
- **Base token:** `Tk0pb8oQ6af9Rxs1fyGliS52gDd`
- ATLAS Atoms table: `tblm5rH3VpSozRPr`
- ATLAS Atom Rules table: `tblHLfiAAq2iULwh`
- ATLAS Molecules table: `tblLU8XRKH5vlmVe`
- Precedents table: `tbl82kDoPuUCa1gu`
- Pending Cases table: `tblcELXmNsmGXlIa`
- Issue scope: **NSA** (same ATLAS atoms shared)
- Schema differences vs SV: uses `object_id` (not `source_video_id`), has `user_nickname`, `user_bio`

### Bitable rule counts (post-2026-05 HRA ingest)
- ATLAS Atoms: 264 total (NSA-tagged: 73, HHB-tagged: 94, HRA-tagged: 118; shared across verticals)
- ATLAS Molecules: 104 total (NSA: 0, HSS: 44, BPI: 40, HRA: 20)
- ATLAS Atom Rules: 3,388 total
  - NSA Active (tax_version `v2.1.0`): 1,260
  - NSA Deprecated (tax_version `v2.0.0`): 93
  - HSS Active (tax_version `v2.0.0`): 145
  - BPI Active (tax_version `v2.0.0`): 109
  - HRA Active (tax_version `v2.1.0`): 1,781

---

## 3. Architecture cheat-sheet

```
┌─────────────────────────────────────────────────────────────────┐
│  index.html  (single-file React 18 via CDN, no JSX)             │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐   │
│  │ Pending picker   │→ │  AtomTagger      │→ │  Retriever   │   │
│  │ (issue-scoped)   │  │  (7-dim DimRow)  │  │  (dual-chan) │   │
│  └──────────────────┘  └──────────────────┘  └──────────────┘   │
│                                                       │         │
│                              ┌────────────────────────┘         │
│                              ▼                                  │
│                   ┌────────────────────────┐                    │
│                   │  Payload builder       │                    │
│                   │  (case-review-payload  │                    │
│                   │   v0.7 + _route_hint)  │                    │
│                   └────────────────────────┘                    │
│                              │                                  │
│            ─ ─ ─ paste to Mira → skill → JSON back ─ ─ ─       │
│                              ▼                                  │
│                   ┌────────────────────────┐                    │
│                   │  ReasonedVerdictPane   │                    │
│                   │  (atoms · claim chain  │                    │
│                   │   · verdict · precs    │                    │
│                   │   · watch-outs)        │                    │
│                   └────────────────────────┘                    │
│                              │                                  │
│                              ▼                                  │
│                   ┌────────────────────────┐                    │
│                   │  ConfirmSaveSection    │                    │
│                   │  (decision override,   │                    │
│                   │   discrepancy detect,  │                    │
│                   │   write to Precedents) │                    │
│                   └────────────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
```

### Image handling (v0.17.x)
- **ImagesPane** — displays first 12 keyframes via SDK `getCellValue`, with expandable "+N more" card
- **Copy keyframes** — uses cached URLs from ImagesPane's prior SDK call (no network calls, instant access); button shows `Math.min(12, total)` count
- **High-image-count fix (v0.17.16)** — `onCopyKeyframes` no longer calls `imageMeta.resolve` with `priority: true` (which bypassed cache and caused SDK timeout)

### Retrieval (dual-channel)
- **BM25** over visual_summary + asr_text + ocr_text + caption_text
- **Atom-Jaccard** between candidate's tagged atoms and each precedent's atoms
- Each channel returns top 4. Merged & deduped → max 8 precedents.

### Payload v0.7 schema highlights
```jsonc
{
  "schema": "case-review-payload",
  "version": "0.7",
  // NEW in v0.7: structural_stability with counterfactual fragility
  "_route_hint": "nsa-atom-precedent-review",  // or "hhb-atom-precedent-review" or "hra-atom-precedent-review"
  "policy_area": "NSA",  // or "HHB" or "HRA"
  "candidate":     { /* visual_summary, asr_text, ocr_text, caption_text, draft atoms */ },
  "rule_book_ref": { "version": "v1.0", "policy_area": "NSA" },
  "engine_simulation": { "verdict": "...", "fired_claims": [...] },
  "precedents":    [ /* ≤ 8, each with capped text fields */ ]
}
```

**v0.7 change:** `claims_slice` removed from payload — non-approve claims are baked into each skill's Appendix B. Typical payload: **15–30 KB** (down from 211 KB).

### Write-back (Confirm & Save)
On save, the plugin:
1. Creates a new record in the **Precedents** table with all case data, atom links, decision, analyst
2. Copies keyframe attachments (reuses file tokens within same base)
3. Detects discrepancy (user decision vs engine/skill expected) and writes `override_tag` field
4. Updates the **Pending Cases** record status to `"Reviewed"`

---

## 4. CSS architecture quirks

The plugin has two separate "DimRow" patterns:

| Selector | Used by | Layout |
|---|---|---|
| `.dim-row` (lines 54–67) | AtomTagger | `display:grid; grid-template-columns:32px 1fr` |
| `.reasoned-card .dim-row` (lines 121–135) | ReasonedVerdictPane | `display:flex` |

`.verdict-pill` and `.conf-chip` are kept in proportional rhythm.

---

## 5. Phase 7 roadmap — verdict-to-action loop

### Implemented ✅

- **7a — Write-back to Precedents table** — Confirm & Save UI, field mapping, attachment copy
- **7b — Decision override** — dropdown for decision + policy_title, discrepancy detection
- **Pending status update** — sets status="Reviewed" after save
- **Override tracking** — `override_tag` field written when user overrides engine/skill decision

### Remaining

- **7c — Engine refresh on edited atoms** — re-run local engine after atom edits, show before/after verdict
- **7d — Atom-disagreement learning signal** — separate `Atom Disagreements` table for per-atom precision/recall tracking
- **7e — Retrieval feedback** — per-precedent usefulness mark
- **7f — Operational metrics dashboard** — sparklines, verdict distribution, agreement %

### Out of scope for phase 7
- Bulk review mode (queue ≥ 10 pending cases batched)
- Evaluator ensemble (skill twice, compare) — costly
- Catalog versioning / migration tooling — not until v1.1 ships

---

## 5b. Phase B — Defensibility Framework (structural fragility + skill ambiguity)

### Implemented (v0.17.17)

- **Counterfactual engine** (`computeCounterfactual` IIFE) — deterministic single-atom flip analysis
  - Strategy 1: remove each tagged atom (all 7 dims) and re-evaluate
  - Strategy 2: near-miss gate fill (claims missing exactly 1 gate dim)
  - Strategies 3-4 (M/X flips) intentionally excluded — they test rule-book design, not content ambiguity
  - Budget: MAX_EVALS = 20; early-exit if Strategy 1 finds a flip
  - Output: `{ structurally_fragile, min_flips_to_inverse, nearest_flip_path, fragility_score }`
- **Payload integration** — `structural_stability` object in payload v0.7 merges DI + counterfactual
- **UI indicators**:
  - Engine-side: yellow "fragile (1-flip)" pill when `structurally_fragile === true`
  - Skill-side: "skill: L2" pill when skill provides `ambiguity_assessment.classification`
- **Debug sections** — two collapsible panels (Structural Fragility, Ambiguity Assessment)
- **Save write-back** — `structurally_fragile` boolean written to Precedents table on Confirm & Save
- **Verdict schema** — `ambiguity_assessment` added as optional field in `atom-verdict.schema.json`

### Implemented (v0.18.0)

- **Defensibility consolidation** — merged three overlapping signals into a two-pillar model:
  - Pillar A: **Decision Rule Stability** (engine-side, deterministic) — SSS composite + counterfactual fragility
  - Pillar B: **Content Ambiguity** (skill-side, LLM reasoning) — expanded `ambiguity_assessment` with `precedent_support` field
  - Merged output: single **Defensibility** tier (HIGH/MEDIUM/LOW) via `computeDefensibility()`
- **`confidence` field deprecated** — removed from skill output and UI; useful signals absorbed into `ambiguity_assessment`
- **New `precedent_support` field** — "strong"/"partial"/"none" inside `ambiguity_assessment`
- **Classification floor rules** — none→≥L2, partial+split→≥L2, flip>0.5+above→L3
- **UI redesign** — replaced AI SKILL vs ENGINE dual-row with single Defensibility pill + expandable two-pillar detail
- **Skills version bump** — NSA v1.7, HHB v1.3, HRA v1.3

### Design decisions

| Decision | Rationale |
|----------|-----------|
| M/X flips excluded | modifier_excluded and exception atoms exist by design to flip claims; testing them would flag ~every non-approve case |
| Engine = "structural fragility" | Engine can only test structural properties (flip distance), not content semantics |
| Skill = "ambiguity assessment" | Content-grounded reasoning about atom confidence, contextual coherence, precedent divergence |
| Two-layer architecture | Engine pass is cheap (<1ms, deterministic); skill pass is expensive but content-aware |
| fragility_score is binary | 0.0 (fragile) or 1.0 (robust) — no gradient because min_flips is always 1 or Infinity with current strategies |
| conf dropped | Single holistic integer offered no actionable insight beyond what classification + precedent_support already convey |
| "AI SKILL vs ENGINE" framing removed | Engine is not an independent opinion — it's a deterministic function of the reviewer's atom selection |
| Defensibility = merged pill | Reviewers need one signal, not three competing badges |

### Remaining

- ~~**Skills emit `ambiguity_assessment`** — update NSA/HHB/HRA skill SKILL.md to include this field in their verdict output~~ ✓ (v1.6/v1.2/v1.2)
- **Bitable field** — add `structurally_fragile` Checkbox field to Precedents table in both bases
- **Governance gate** — policy-team workflow rule: fragile + L2/L3 → mandatory escalation
- **Fragility gradient** — future: multi-flip distance (2-flip, 3-flip) for finer scoring

---

## 6. Recent UI changes (v0.16-v0.17)

- **Precedent analysis** — sorted by applicability tier (APPLICABLE → PARTIAL → NON-APPLICABLE), NON-APPLICABLE collapsed in nested `<details>`
- **Atom chips** — display `atom_name` for readability, `atom_key` in tooltip
- **Debug consolidation** — version info, Engine I/O, Claim gate diagnostics, Selected atom_keys all moved into collapsed sections ("Debug tools" inside tagger, "Debug & Info" at footer)
- **Confirm & Save section** — decision/policy override, rationale, save button, discrepancy warning banner
- **ImagesPane (v0.17.x)** — expandable "+N more" card for cases with >12 images; cached URL access; copy-keyframes-from-cache fix
- **UX fixes (v0.17.17)** — expanded state in ImagesPane, Copy keyframes button shows `min(12, total)` count

---

## 7. Known constraints / gotchas

- **No JSX** — everything goes through `e = React.createElement`. Don't break this.
- **No bundler / build step** — React 18 + Babel-free CDN. Inline script must be ES2018-compatible.
- **Skill is fully self-contained** — never reintroduce sibling-file fetches. The Appendix JSON in `SKILL.md` is the source of truth.
- **Atom-key form** is canonical dotted-namespace (`atom.not_applicable`, `subject.adult`). `serial_code` strings (`"C37 — Not applicable"`) are display-only.
- **`final_policy_title`** is `null` when undecided, never `"None"` or empty string.
- **`engine_alignment.engine_verdict`** must mirror `engine_simulation.verdict` from the input payload.
- **Link fields** for atom write-back use `[{ recordId: "..." }]` format (Bitable Block SDK).
- **Attachment copy** reuses file tokens within the same base — no re-upload needed,
  **but** the tokens must come from `pendingTbl.getCellValue(imgFieldId, srcRecId)` at save time,
  not from the React-side `pendingCase.images` (that path is normalized through `cellAttachments()`
  which flattens the SDK-native object to `{token,name,type,size,url}` and the SDK silently drops
  writes for the flattened shape). See v0.16.10 source-cell re-read.
- **SingleSelect / MultiSelect writes** require the Block SDK shape `{id, text}` resolved from
  `m.property.options` at field-meta load time. Bare strings and bare `{text}` both silently drop
  on `table.addRecord`. See v0.16.7 `buildFieldIndex.selectOptions` + setSmartField option-ID resolution.
- **REST file_tokens are NOT interchangeable with SDK-context tokens.** `bitable_upload_sdk` crashes
  with `p.createReader is not a function` when asked to validate a REST token. If you ever need to
  ingest external images into a Bitable attachment cell, mint tokens through `bitable.bridge.uploadAttachment`
  (when exposed) — never inject REST file_tokens directly.
- **SDK silent-acceptance trap (CRITICAL).** Block SDK `addRecord` / `setRecord`
  / `field.setValue` return success for shapes they can't honor, then no-op the
  cell. The try/catch fallback pattern is useless against this — there's
  nothing to catch. Confirmed for SingleSelect (v0.16.7), MultiSelect (v0.16.7),
  Attachment (v0.16.10), and SingleSelect-via-setRecord on a sibling table
  (v0.16.13). Always:
  1. Route Select/MultiSelect writes through `setSmartField`, OR resolve
     `{id, text}` from `pidx.selectOptions[fieldId].byName` inline before
     calling `setRecord`. Bare strings and bare `{text}` both drop silently
     on this SDK build.
  2. For attachments, read the source cell with `getCellValue` and pass the
     raw value through — never re-normalize. Flattening to
     `{token,name,type,size,url}` loses the SDK-internal File handle.
  3. For links, use `{recordIds, tableId}` where `tableId` comes from
     `idx.linkTableIds[fId]` (captured at `buildFieldIndex` time).
- **One writer, one shape contract.** Any new code path that talks to the
  Bitable SDK MUST route through `setSmartField` / `setTextField` (precedent
  table) or the option-id-resolution pattern used in the pending-status block
  (v0.16.13). Hand-rolling a `setRecord({fields: {[id]: rawValue}})` call from
  a new feature is how v0.16.13 regressed — the pending-row update was added
  *after* the v0.16.7 SingleSelect lesson was learned but didn't apply it.
- **Never run regex-based "cleanup" patches on `plugin/dist/index.html`.** The file is large and
  tightly-coupled; a single greedy `re.DOTALL` match deleted ~59 KB of legitimate code in one shot
  (post-mortem: v0.16.11 cleanup attempt, 2026-06-01). Always use exact-string `Edit` against named
  anchors with a byte-size assertion on the result.

---

## 8. Repo file inventory

```
case_review_atom_mvp/
├── CHANGELOG.md                         — version-by-version changes
├── Labelgpt/                            — pending-case pre-labelling (APV parser + prompt)
│   ├── apv_parser.py
│   └── labelgpt_prompt_v0.4.md
├── MIRA_SETUP.md                        — Mira project onboarding guide
├── PROJECT_NOTES.md                     — this file (current-state snapshot)
├── REVIEW_AND_DESIGN.md                 — historical design proposal (pre-implementation)
├── context/                             — read-only reference inputs (EXCLUDED)
│   ├── agent014-atlas-main/             — upstream Atlas repo snapshot
│   └── atlas-export-{nsa,hss,bpi}-all_titles-2026-05-15-CORRECTED.json
├── docs/
│   ├── engine-spec.md                   — deterministic engine spec
│   └── payload-schema.md                — case-review-payload v0.7 reference
├── plugin/
│   ├── manifest.json                    — Bitable extension manifest (v0.17.1)
│   └── dist/
│       └── index.html                   — single-file plugin build (~224 KB)
└── skills/
    ├── nsa-atom-precedent-review/
    │   ├── SKILL.md                     — skill v1.6 with inlined atoms_catalog + claims
    │   ├── nsa-atom-catalog.json        — reference copy (NOT runtime-loaded)
    │   ├── nsa-claims-non-approve.json  — reference copy (NOT runtime-loaded)
    │   └── schema/atom-verdict.schema.json
    ├── hhb-atom-precedent-review/
    │   ├── SKILL.md                     — skill v1.2 with inlined atoms_catalog + claims
    │   ├── hhb-atom-catalog.json        — reference copy (NOT runtime-loaded)
    │   └── hhb-claims-non-approve.json  — reference copy (NOT runtime-loaded)
    └── hra-atom-precedent-review/
        └── SKILL.md                     — skill v1.2, 252 non-approve claims, 118 atoms
```

---

## 9. Scheduler prefill channel (NEW 2026-05-25)

Backend scheduler can now hand off a composite keyframe image to the specialist skills via URL rather than relying on the human reviewer to paste a clipboard image.

### Payload field
- `candidate.composite_image_url` *(optional)* — Mira-hosted PNG (composite of up to 12 keyframes, 2-col grid, ~7d TTL) generated by the prefill scheduler. Manual chat-paste flows leave this field absent.

### Skill behaviour (NSA + HHB + HRA, all three patched)
- All three precedent-review skills had their hard `Web Fetch` ban narrowed in 2026-05-25 republish to permit fetching that one URL.
- Image-handling precedence inside the skill: chat-attached image > `composite_image_url` > `visual_summary` text-only.
- Skill keys republished (versions unchanged): `nsa-atom-precedent-review`, `hhb-atom-precedent-review`, `hra-atom-precedent-review`.

### Verification notes
- Filesystem verification on `/data/plugins/custom/skills/nsa-atom-precedent-review/SKILL.md` (2026-05-25) confirms patched ban + composite_image_url fetch fallback are live.
- **Caveat**: the agent's loaded skill text appears to be snapshotted at session-start, so behavioural verification of the fetch path must be run in a fresh agent session — same-session Skill calls keep using the pre-republish snapshot.

### Remaining work
- Plugin "Request prefill" button to trigger the scheduler.
- Scheduler prompt template that builds the composite, uploads it, and writes the URL back to the Pending Cases row.

