# Mira Project Setup Checklist — "AI Policy"

This checklist covers the **one-time UI-side steps** you need to do in the Mira app
to finish wiring `case_review_atom_mvp` into your "AI Policy" project. The repo
side (README, `.mira/project.yaml`, sandbox copy) is already done.

---

## Already done (by Mira, automated)

- [x] Cleaned `.DS_Store` files from the local repo
- [x] Created `~/Documents/Rich/case_review_atom_mvp/README.md`
- [x] Created `~/Documents/Rich/case_review_atom_mvp/.mira/project.yaml`
- [x] Seeded persistent sandbox copy at `userdata/1132591/case_review_atom_mvp/`
- [x] Excluded `context/**` (the 19 MB reference tree) from the sandbox copy

---

## Manual steps in the Mira UI (you, ~2 minutes)

### Step 1 — Attach the 3 pinned files to the "AI Policy" project
Open the "AI Policy" project in Mira, then upload/attach these from your local repo:

1. `~/Documents/Rich/case_review_atom_mvp/PROJECT_NOTES.md`
2. `~/Documents/Rich/case_review_atom_mvp/docs/payload-schema.md`
3. `~/Documents/Rich/case_review_atom_mvp/docs/engine-spec.md`

These are the contract surface — they should always be in context when you open
a session inside "AI Policy".

### Step 2 — Set the project description (optional)
In the project settings, paste:

> NSA-only ATLAS Atom Rules console. Local repo at `~/Documents/Rich/case_review_atom_mvp`.
> Sandbox copy at `userdata/1132591/case_review_atom_mvp`. Pin/exclude rules live in
> `.mira/project.yaml`. Local is source of truth; sandbox is mtime-synced.

### Step 3 — Verify on next session open
Start a fresh chat inside "AI Policy" and ask:

> "Confirm the project is wired: list pinned files, sandbox path, and mtime status."

Expected: the 3 pinned `.md` files load automatically, sandbox path matches
`userdata/1132591/case_review_atom_mvp/`, and mtime check shows "in sync".

---

## Refresh ritual (when you cut a new plugin/skill version)

When `CHANGELOG.md` gets a new version entry, spend 30 seconds:

> "Mira, the project bumped to v0.7.5. Re-evaluate the pin list against the current local directory."

I'll scan, propose adds/removes (e.g., new `docs/phase7-spec.md`), you approve.

---

## Quick reference

| Path | Role |
|---|---|
| `~/Documents/Rich/case_review_atom_mvp/` | **Local source of truth** — edit here |
| `userdata/1132591/case_review_atom_mvp/` | **Sandbox copy** — auto-synced, in-session reads |
| Mira "AI Policy" project | **Cloud project** — pinned files, persistent across sessions |

| Document | Purpose |
|---|---|
| `README.md` | Landing page; orients newcomers |
| `.mira/project.yaml` | Pin/exclude rules + sync strategy |
| `PROJECT_NOTES.md` | Living state snapshot (PINNED) |
| `docs/payload-schema.md` | Plugin<->skill contract (PINNED) |
| `docs/engine-spec.md` | Engine simulation contract (PINNED) |
| `CHANGELOG.md` | Version history (read on demand) |
| `REVIEW_AND_DESIGN.md` | Original design (HISTORICAL) |
