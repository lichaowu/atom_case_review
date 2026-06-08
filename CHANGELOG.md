# case_review_atom_mvp — Changelog

NSA-only ATLAS Atom Rules Bitable plugin. Tracks the React-CDN single-file plugin (`plugin/dist/index.html`) and the bundled NSA atom-precedent-review skill (`skills/nsa-atom-precedent-review/SKILL.md`).

---

## v0.7.4-phase6a — 2026-05-19 *(current)*

**Theme:** Retrieval breadth tuning.

- **Plugin:** `plugin/dist/index.html`
  - Retrieval call (`AtomRetriever.retrieve`) reduced from `topPerChannel: 5, totalK: 10` → `topPerChannel: 4, totalK: 8`. Two channels (BM25 keyword + ATLAS atom-Jaccard) → top 4 each → merged & deduped → ≤ 8 precedents.
  - Combined with v0.7.3 per-precedent text caps, drops the precedent body ceiling from ~49 KB → ~39 KB.

## v0.7.3-phase6a — 2026-05-19

**Theme:** UI consistency and payload trim.

- **Plugin:** `plugin/dist/index.html`
  - **Pending-case dropdown** now leads with `issue` (e.g., `NSA`), then `policy_title` (or `(untitled)`), then `source_video_id`, then a 60-char visual-summary preview. Replaces the prior `?`-prefix label.
  - **AtomTagger DimRow CSS scoping fix.** Two `.dim-row` rules were colliding via cascade — the verdict-pane block now lives under `.reasoned-card .dim-row` so AtomTagger's grid layout (`32px 1fr`) survives unchanged.
  - **`.verdict-pill` proportions matched to `.conf-chip`:** `padding:5px 12px; font-size:11px; line-height:1.3` (was `8px 14px / 13px`). Fixes uneven visual rhythm in the verdict header.
  - **Payload size reduction (122 KB → ~30–45 KB):**
    - New `_cap()` helper with constants `PREC_VS_CAP=1500`, `PREC_TEXT_CAP=800`, `PREC_RAT_CAP=1000`. Each precedent's `visual_summary`, `asr_text`, `ocr_text`, `caption_text`, `rationale` is capped with a `…[truncated +N chars]` marker.
    - Dropped redundant fields: `record_id` per precedent; verbose `note` strings from `engine_simulation`, `claims_slice`, `rule_book_ref`; redundant `topic` from candidate.
  - Plugin version bumped to `atom-mvp v0.7.3-phase6a`.

- **Skill:** `skills/nsa-atom-precedent-review/SKILL.md` → **v1.3 (atoms_catalog inlined, claims sliced)**
  - **Catalog inlined.** Slim 22 KB JSON block at the Appendix containing all 73 atoms across C/S/P/R/E/M/X with `{atom_key, atom_name, serial_code, description}`. `audit_rule` dropped (uniform per dim, retained in the `dimensions[]` block).
  - **No-tool-use directive** added near the top: "Do NOT call `Web Fetch`, web search, `Bash`, `Read`, `Grep`, `Glob`, or any file-search tool." Eliminates the v1.2 failure mode where the skill tried to fetch the sibling JSON file.
  - **Output schema clarifications:** canonical dotted-namespace atom keys (never `serial_code`); `final_policy_title: null` when undecided; `engine_alignment.engine_verdict` mirrors `engine_simulation.verdict`.

## v0.7.2-phase6a — 2026-05-19

- **Plugin:** ReasonedVerdictPane swapped to v0.7.1 layout — catalog lookup, collapsible textarea, color-coded confidence chip, conditional final_policy_title rendering, engine-verdict fallback. Mount site updated to pass `atomsByDim: corpus.atomsByDim`.

## v0.7.1-phase6 — earlier 2026-05

- New ReasonedVerdictPane prototype as `/tmp/new_pane.js` (~270 lines), pre-injection.

## v0.6.x and earlier

- Phase 5: payload schema v0.6 with `_route_hint`, `claims_slice`, `rule_book_ref`.
- Phase 4: dual-channel retriever (BM25 + atom Jaccard).
- Phase 3: AtomTagger UI with 7-dim DimRow grid.
- Phase 2: NSA atom catalog ingestion (73 atoms, 7 dims).
- Phase 1: Bitable plumbing (Cases, Pending Cases, Atom Rules tables).

---

## Deliverables — current build

| Asset | Path | Size |
|---|---|---|
| Plugin | `plugin/dist/index.html` | ~157 KB |
| Skill | `skills/nsa-atom-precedent-review/SKILL.md` | ~43 KB |
| Skill catalog (sibling, kept for reference) | `skills/nsa-atom-precedent-review/nsa-atom-catalog.json` | ~43 KB |
| Verdict schema | `skills/nsa-atom-precedent-review/schema/atom-verdict.schema.json` | ~1 KB |

Latest plugin upload URL: see `PROJECT_NOTES.md § 2`.

---

## Phase 7 — planned

See `PROJECT_NOTES.md § 5 — Phase 7 roadmap`. Headline: close the verdict→action loop (persist verdicts back to Bitable, reviewer override UX, atom-disagreement learning signal).

---

## Doc maintenance log

- **2026-05-21** — Doc-alignment pass: removed obsolete `_skill/` directory and `SKILL.md.pre-v1.3.bak`; refreshed paths in this file and in `PROJECT_NOTES.md`; rewrote `docs/payload-schema.md` from v0.1 to v0.6; bumped `plugin/manifest.json` to 0.7.4; stamped `REVIEW_AND_DESIGN.md` as historical (post-implementation).
