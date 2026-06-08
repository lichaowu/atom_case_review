# Deterministic Atom-Rule Engine — Spec

Plugin: `case_review_atom_mvp`. Consumes `(caseAtoms, claims[])`; emits
`EngineResult` (see `payload-schema.md`).

## 1. Inputs

```ts
type AtomKey = string;                    // e.g. "C1", "M5"
type AndGroup = AtomKey[];                // ["M4","M5"] = M4 ∧ M5
type Dnf = AndGroup[];                    // [["M4","M5"], ["M7"]] = (M4∧M5) ∨ M7

interface CaseAtoms {
  C: AtomKey[]; S: AtomKey[]; P: AtomKey[]; R: AtomKey[];
  E: AtomKey[]; M: AtomKey[]; X: AtomKey[];
}

interface Claim {
  claim_id: string;
  policy_titles: string[];
  issue: string;
  outcome: "VIOLATION" | "NOT_RECOMMEND" | "NOT_FOR_FEED" | "APPROVE";
  status: string;
  gates: { C: AtomKey[]; S: AtomKey[]; P: AtomKey[]; R: AtomKey[]; E: AtomKey[] };
  modifiers_required: Dnf;          // legacy AND-list = single group; multi-group = OR-of-ANDs
  modifiers_excluded: AtomKey[];
  modifiers_lift_dnf: Dnf;
  exceptions_required: AtomKey[];
  exception_qualifiers: Record<AtomKey, Dnf>;
  exception_qualifier_modifiers: Record<AtomKey, Dnf>;
  requires_exception_context: boolean;
  exceptions_lift_to_approve: boolean;
  routing: { non_realistic_routes_to: string|null; cross_title_redirect: string|null };
}
```

## 2. Stage 1 — Gate evaluation (per claim)

```
gateHit(claim, case) :=
  ∀ d ∈ {C, S, P, R, E}:
    claim.gates[d] = ∅  ∨  (case[d] ∩ claim.gates[d] ≠ ∅)
```

If `claim.requires_exception_context` is true, additionally require
`case.X ∩ claim.exceptions_required ≠ ∅`.

## 3. Stage 2 — Lifts (applied in this exact order)

For each claim that gate-hit:

1. **Excluded modifier** — if `case.M ∩ claim.modifiers_excluded ≠ ∅` → suppress claim.
2. **Required modifier** — if `claim.modifiers_required` non-empty and
   no group `g` satisfies `g ⊆ case.M` → suppress claim.
3. **Modifier lift to approve** — if any group in `claim.modifiers_lift_dnf`
   satisfies `g ⊆ case.M` → outcome becomes `APPROVE`, `lift = "modifier"`.
4. **Exception lift to approve** — if `claim.exceptions_lift_to_approve` and
   ∃ x ∈ `claim.exceptions_required ∩ case.X` such that
   - some group in `exception_qualifiers[x]` ⊆ allCaseAtoms (any dimension), AND
   - some group in `exception_qualifier_modifiers[x]` ⊆ case.M
   → outcome becomes `APPROVE`, `lift = "exception:" + x`.

If no lift applies, outcome = `claim.outcome`.

## 4. Stage 3 — Severity & ordering

Across all surviving claims:

- `SEVERITY = { VIOLATION:4, NOT_RECOMMEND:3, NOT_FOR_FEED:2, APPROVE:1 }`
- Sort descending by:
  1. `SEVERITY[outcome_after_lifts]`
  2. `specificity = |gates.C| + |gates.S| + |gates.P|`  (more specific wins ties)
  3. `claim_id` ascending  (stable lexicographic tie-break)

`engine_result.verdict` = top-sorted claim's outcome, or `"NO_CLAIM_FIRED"` if zero claims survive.
`engine_result.applied_claim_chain` = `[claim_id_of_top_claim]`. Multi-claim
chains (V0.2) are out of scope.

## 5. Routing

`engine_result.routing` is populated from the top claim's `routing` field.
**Routing pointers do NOT change `verdict`** — they are reviewer hints only.

## 6. Determinism guarantees

- Pure function of `(caseAtoms, claims[])` — no random, no clock, no I/O.
- Stable ordering: ties broken by `claim_id` ascending.
- Status filter: claims with `status != "active"` are filtered out at load time
  (not at engine time).
- Empty gate dimension = wildcard. Claims with all five gate dimensions empty
  are rejected at load time (would match every case).

## 7. Test fixtures

Minimum fixtures for unit tests (under `plugin/dist/test/` once Phase 3 lands):

| fixture                  | inputs                                        | expected verdict |
|--------------------------|-----------------------------------------------|------------------|
| AN.001 base hit          | C1, S1, P11, R1, M5, M4                       | VIOLATION        |
| AN.001 + X1 lift         | + X1, qualifier modifiers M4                  | APPROVE          |
| AN.001 excluded modifier | C1, S1, P11, R1, M_excluded                   | NO_CLAIM_FIRED   |
| Empty atoms              | (all empty)                                   | NO_CLAIM_FIRED   |

## 8. Invariants (per AIPRB §A5.2 Phase F)

1. Same input → same output.
2. Routing pointer never overrides severity.
3. `outcome_after_lifts` ∈ engine outcome alphabet.
4. `verdict ≠ "NO_CLAIM_FIRED"` ⇒ `applied_claim_chain.length ≥ 1`.

## 9. Counterfactual fragility analysis (Phase B)

Module: `computeCounterfactual(caseAtoms, claims, currentVerdict, opts?)`

A companion to the main engine that answers: *"Is this verdict structurally
fragile — can removing or adding a single gate-level atom invert the outcome?"*

### 9.1 Inputs

Same `(CaseAtoms, Claim[])` as the main engine, plus:
- `currentVerdict` — the verdict to test fragility against.
- `opts.policy_title` — optional scoping filter (only test claims for this title).

### 9.2 Verdict inversion definition

```
isEnforcement(v) := SEVERITY[v] >= 2
verdictFlipped(a, b) := isEnforcement(a) XOR isEnforcement(b)
```

A flip is any transition that crosses the enforcement boundary (APPROVE ↔ anything ≥ NOT_FOR_FEED).

### 9.3 Strategies

| # | Name | Description | Atoms tested |
|---|------|-------------|--------------|
| 1 | Remove each tagged atom | For each atom in `caseAtoms[d]` (d ∈ C,S,P,R,E,M,X), remove it and re-evaluate | All 7 dims |
| 2 | Near-miss gate fill | Find claims missing exactly 1 gate dimension; add the missing atom and re-evaluate | C,S,P,R,E only |

**Excluded strategies (by design):**
- ~~Strategy 3: Add modifier_excluded~~ — M_excluded atoms are designed to suppress claims; their mere existence in the catalog would flag nearly every non-approve case.
- ~~Strategy 4: Remove exception atoms~~ — Exception atoms are rule-book escape paths. Testing them measures rule completeness, not content ambiguity.

### 9.4 Evaluation budget

`MAX_EVALS = 20`. Strategies execute in order; evaluation stops once the budget
is exhausted. Strategy 2 only runs if Strategy 1 found zero flips (early-exit
optimization).

### 9.5 Output

```ts
interface FragilityResult {
  structurally_fragile: boolean;     // true if any 1-atom flip inverts verdict
  min_flips_to_inverse: 1 | Infinity;
  nearest_flip_path: FlipStep[] | null;
  evals_run: number;
  fragility_score: 0.0 | 1.0;       // 0.0 = fragile, 1.0 = robust
}

interface FlipStep {
  action: "remove" | "add";
  dim: string;          // "C", "S", "P", "R", "E", "M", "X"
  atom_key: string;     // canonical dotted-namespace
  resulting_verdict: string;
}
```

### 9.6 Relationship to skill-side ambiguity

Structural fragility is a **cheap, deterministic, structural signal** (<1ms,
no LLM call). It cannot assess atom confidence or contextual coherence.

True ambiguity assessment is the skill's responsibility. The skill outputs
an `ambiguity_assessment` object in its verdict JSON (see `atom-verdict.schema.json`):
- `classification`: L1 (low) / L2 (moderate) / L3 (high)
- `flip_plausibility`: 0.0–1.0 (how plausible is it that the content genuinely
  supports the alternate interpretation?)
- `factors[]`: human-readable reasons (e.g., "mixed visual signals", "borderline age")
- `weakest_atoms[]`: which atoms have lowest tagging confidence

**Governance gate:** both engine fragility AND skill ambiguity should be
favorable for a case to pass without escalation.

### 9.7 Determinism guarantees

Same as the main engine (§6): pure function, no random, no clock, no I/O.
Stable: ties in Strategy 2 broken by claim iteration order.
