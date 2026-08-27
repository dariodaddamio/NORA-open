# Development preferences (NORA)

NORA is a Python-first private repo. Full Opifex TypeScript prefs live in the Opifex preset; this file holds what NORA agents need locally.

## Authored copy register (required)

Write like Google developer documentation: **dead prose**. No aphorisms. No
flourishes. Simple sentences. Technical terms when they are the actual terms.
Subject-verb-object facts. No punchy openers, metaphor, or theater.

**Clear sentence shape.** Use clear subject/verb/object constructions. Do not
use cleft sentences, contrastive appositives, appended glosses, or trailing
clauses that restate or soften the claim.

**No staccato.** Do not generate equative stacks, directory-legend lines, or
telegram fragment paragraphs.

Do **not** define by negation. Ban contrast pairs of the form “X, not Y”.
State what the thing is and what it does.

**Human-editable documents.** Assume the user may edit documents directly,
especially markdown. Write so a human can revise the file without decoding
agent session context.

**No private conversation references in markdown.** Durable markdown must not
cite chat threads, agent sessions, or other conversation identifiers a later
reader would not know. Record durable decisions in prefs, ADRs, and catalogs.
Keep session leftovers on the wipe-gate ledger only.

Opifex SoT detail: Opifex `docs/preferences/development.md` → Authored copy
register.

## Anti-slop (machine-gated)

Machine-gated detection of the ten AI slop tendencies plus a planning-time
scope-allowlist table in the wipe-gate ledger. Agents list intended paths and
tendency checks before code lands. There is **no** PreToolUse write-blocking
scope-guard hook and agents must not reintroduce one. Scope discipline is
planning plus `pnpm check:anti-slop` (advisory), not edit denies.

### Ten slop tendencies

1. **Over-engineering solutions.** Adding layers, abstractions, or subsystems the user did not ask for. Fix: state the smallest coherent change, name the trade-off, do not invent extra structure.
2. **Overly defensive programming.** Bare `try { } catch {}`, silent fallbacks, redundant null guards around already-typed values. Fix: validate at the trust boundary, then trust the type.
3. **Hyper-fixation on rare or fictitious edge cases.** Branches for inputs the system never receives. Fix: name the evidence (where does this input come from?) or delete the branch.
4. **Subsystem responsibilities overlap.** Two modules own the same invariant or transform. Fix: name the canonical owner; let the other module read it.
5. **Solving problems at the wrong architectural layer.** UI doing domain logic, hooks doing UI, tests doing implementation. Fix: read `docs/file-catalog.json` for the file role before adding code.
6. **Duplicate sources of truth, then sync machinery.** Two stores hold the same value and a reconcile loop keeps them aligned. Fix: one store; let the others read it.
7. **Prematurely generalizing one-off flows.** Parameterizing a path that has exactly one caller today. Fix: leave it concrete until the second caller arrives.
8. **Timeouts on everything.** Wrapping arbitrary async in `setTimeout` or `AbortSignal.timeout` without an outbound-HTTP reason. Fix: explicit timeouts only on outbound HTTP per the Errors and failure policy in this file.
9. **Production code that exists purely to satisfy tests.** Exports, factories, or branches whose only caller is a test. Fix: kill the production code or kill the test.
10. **Patching bad premises additively.** When the premise is wrong, adding code on top instead of deleting the premise. Fix: delete the bad premise in the same change; do not paper it over.

### Scope CLI and audit

- `pnpm check:anti-slop` reads the scope-allowlist table and prints warnings (advisory).
- `pnpm check:process` includes `anti-slop` when present.
- Do not add `pnpm scope:include` or a session-scope write-deny hook.

Skill SoT: `.cursor/skills/anti-slop/SKILL.md`. The skill is planning-time intent; `check:anti-slop` is the advisory audit.
