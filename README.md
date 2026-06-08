# case_review_atom_mvp

ATLAS Atom Rules Bitable plugin + companion specialist skills (NSA + HHB scope).
Sibling of `case_review_mvp` (which targets the legacy V0.3 collapsed-tier rule book).

**Mira Project:** *AI Policy*
**Current build:** `atom-mvp v0.10.0-writeback` (2026-05-22) · skills `nsa-atom-precedent-review v1.4` + `hhb-atom-precedent-review v1.0`

---

## Where to look first

| If you want to... | Read |
|---|---|
| Understand the **current state** | [`PROJECT_NOTES.md`](./PROJECT_NOTES.md) |
| See **what changed** between versions | [`CHANGELOG.md`](./CHANGELOG.md) |
| Reference the **payload contract** (plugin ↔ skill) | [`docs/payload-schema.md`](./docs/payload-schema.md) |
| Reference the **engine simulation contract** | [`docs/engine-spec.md`](./docs/engine-spec.md) |
| Read the **original design proposal** (historical) | [`REVIEW_AND_DESIGN.md`](./REVIEW_AND_DESIGN.md) |

---

## Layout

```
case_review_atom_mvp/
├── .mira/project.yaml              ← Mira-side pin/exclude rules
├── README.md                       ← this file
├── PROJECT_NOTES.md                ← living state snapshot  (PINNED)
├── CHANGELOG.md                    ← version history
├── REVIEW_AND_DESIGN.md            ← original design (HISTORICAL)
├── docs/
│   ├── payload-schema.md           ← v0.7 contract           (PINNED)
│   └── engine-spec.md              ← engine contract          (PINNED)
├── plugin/
│   ├── manifest.json               ← v0.10.0
│   └── dist/index.html             ← single-file React-CDN plugin (~175 KB)
├── skills/
│   ├── nsa-atom-precedent-review/
│   │   ├── SKILL.md                ← v1.4, atoms_catalog + claims inlined (~100 KB)
│   │   ├── nsa-atom-catalog.json   ← reference only, NOT runtime
│   │   ├── nsa-claims-non-approve.json ← reference only, NOT runtime
│   │   └── schema/atom-verdict.schema.json
│   └── hhb-atom-precedent-review/
│       ├── SKILL.md                ← v1.0, atoms_catalog + claims inlined (~87 KB)
│       ├── hhb-atom-catalog.json   ← reference only, NOT runtime
│       └── hhb-claims-non-approve.json ← reference only, NOT runtime
└── context/                        ← EXCLUDED from Mira project (~19 MB reference snapshot)
    ├── agent014-atlas-main/        ← upstream ATLAS Next.js app (read-only mirror)
    └── atlas-export-*.json         ← canon exports (NSA / HSS / BPI)
```

---

## What the plugin does

A single-file React-CDN Bitable plugin that lets a T&S reviewer:

1. **Pick a pending case** from the `Pending Cases` table (issue-scoped dropdown)
2. **Tag it across 7 ATLAS atom dimensions** (C/S/P/R/E/M/X)
3. **Retrieve precedents** via dual-channel similarity (BM25 + atom-Jaccard)
4. **Build a payload** (v0.7) with route-hint to the correct skill (NSA or HHB)
5. **Paste back** the skill's reasoned verdict JSON and view structured analysis
6. **Confirm & save** to the Precedents table with decision override tracking, discrepancy detection, keyframe copy, and automatic pending-status update

### Policy area routing

| `policy_area` | Route hint | Skill |
|---|---|---|
| NSA | `nsa-atom-precedent-review` | NSA skill v1.4 |
| HHB (HSS + BPI) | `hhb-atom-precedent-review` | HHB skill v1.0 |

---

## Working with this project in Mira

This repo is wired for the **sandbox-first workflow**:

1. **Local is the source of truth.** Edits happen here, in your IDE.
2. **Mira sandbox** (`userdata/1132591/case_review_atom_mvp/`) holds a curated copy for in-session analysis.
3. **Sync rule:** mtime-based, one-directional (local → sandbox/cloud). Never the reverse without an explicit write-back.
4. **Local MCP** is only used for: (a) detecting changes via `stat`, (b) one-shot copy on detected change, (c) final write-back of edits.

The pin/exclude rules live in [`.mira/project.yaml`](./.mira/project.yaml). Glob-based, so new files matching `docs/*.md` or `skills/*/SKILL.md` are picked up automatically next session.

### What's auto-pinned (loads into context on session open)
- `PROJECT_NOTES.md`
- `docs/*.md`
- top-level `*.md` (excluding the historical `REVIEW_AND_DESIGN.md`)

### What's available but on-demand
- `plugin/dist/index.html` — too large to pin; read via grep + line ranges
- `skills/*/SKILL.md` — read on demand when working on the skill
- `CHANGELOG.md` — read when version-walking

### What's excluded entirely
- `context/**` — 19 MB external reference; lives only on local
- `**/node_modules/**`, `**/.DS_Store`, `**/*.log`

---

## External references (not in this repo)

| Name | Where | Purpose |
|---|---|---|
| ATLAS upstream app | mirrored in `context/agent014-atlas-main/` | Source-of-truth for atom canon and tests |
| Bitable: AI Policy Rule Book | base token in PROJECT_NOTES | Atoms / Atom Rules / Molecules / Precedents / Pending Cases |
| Sibling plugin | `case_review_mvp/` | Legacy V0.3 collapsed-tier console |
