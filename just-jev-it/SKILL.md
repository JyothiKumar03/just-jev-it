---
name: just-jev-it
description: Audit an EXISTING workflow, agent, automation, or codebase to find LLM call sites and output-branching decision points that TypeSafe AI's Jev model (a non-generative, typed-decision "System One" model) could replace or augment, then plan, execute, and validate the migration. Use when the user asks "can I use Jev for X", "where could I use Jev in this repo", wants to cut LLM cost/latency on classification, routing, triage, moderation, or confidence-gated decisions, or explicitly says "just jev it" / invokes just-jev-it. Do NOT use this for designing or authoring a brand-new Jev integration from scratch with no existing code to audit — that greenfield "build with Jev" task belongs to TypeSafe AI's own official Claude Code skill; this skill's job is auditing what already exists, not scaffolding something new.
license: MIT
---

Audit a user's existing workflow, agent, or automation to find decision
points a real, non-generative Jev call could replace, then plan, execute,
and validate that migration. This skill is for AUDITING code that already
exists — not for designing a new Jev integration from a blank slate (that's
TypeSafe AI's own "build with Jev" skill; if the user has no existing
workflow to point at, tell them so and stop).

Read `references/jev-overview.md` first, in full, before doing anything
else. It explains what Jev actually is, its three typed question
primitives (`noul`/`choice`/`score`), its documented limitations, and why
it is not a drop-in LLM replacement. Every judgment call in this skill
depends on that background.

Work through the four phases below in order. Do not skip Phase 2's
approval gate.

## Phase 1: Audit

Find every LLM call site and every place output from an LLM drives
branching logic in the target workflow/codebase.

1. Grep for LLM call patterns: SDK client calls (`.complete(`, `.chat(`,
   `.invoke(`, `.generate(`), prompt-construction strings, and imports of
   LLM SDKs (`openai`, `anthropic`, `langchain`, etc.).
2. Grep for output-branching near those call sites: `if`/`elif`/`switch`
   statements that test a response string against a small set of values,
   regex matches against a fixed label set, `.strip().lower() in {...}`
   patterns, and fallback branches for malformed responses.
3. Read each call site in full context (the function it lives in, not
   just the matched line) — you need to see what the state/prompt
   actually contains and what the caller does with the result.
4. Classify each call site as **good fit**, **poor fit**, or **needs more
   context** using `references/fit-heuristics.md`. Read that file now if
   you haven't already — it gives the backbone suitability test (decides
   vs. creates, predefined answer space, single focused judgment, fits in
   state, expert-judgeable, consumed by software not displayed as prose)
   plus concrete good/poor-fit code signals and worked before/after
   examples.

Produce a findings table and show it to the user:

| File:Line | Snippet | Verdict | Reason |
|---|---|---|---|
| `app/tickets.py:42` | `if response.strip().lower() not in {"low","medium","high"}: ...` | Good fit | Closed 3-way output space, defensive re-parse of free text into an enum — classic `choice` shape |
| `app/replies.py:18` | `return llm.complete(f"Write a reply to: {ticket}")` | Poor fit | Free text consumed directly by a human; Jev cannot generate prose |

Keep the "Reason" column to one line, but make it specific — cite the
actual signal from `fit-heuristics.md` (e.g. "re-parsed into an enum,"
"confidence threshold already gates the branch," "output is prose
consumed by a human") rather than a generic "looks classifiable."

**If a call site is ambiguous** (e.g. the LLM output is re-parsed into an
enum, but that enum is then interpolated as narrative context into
another LLM prompt), say so explicitly in the table rather than forcing a
verdict — `fit-heuristics.md`'s "Poor Jev Fit" section documents this
exact disguise case and how to tell the two apart.

## Phase 2: Plan

For every finding marked **good fit**, write a concrete before/after
migration plan.

1. Read `references/integration-patterns.md` for the replacement shape
   that matches the target codebase: a plain Python call loop, a
   LangChain chain, or the generic REST fallback for any other framework
   or language. Use the pattern that matches what Phase 1 found — don't
   invent a shape it doesn't cover.
2. For each good-fit finding, write:
   - **Before**: the current code (already captured in the Phase 1 table).
   - **After**: the replacement Jev call, using the exact SDK/REST shape
     from `references/integration-patterns.md` — including its accessor
     convention (`.choices["key"].choice` for the Python SDK,
     `.answers.key` for JS/raw REST — don't mix them) and a `needs_review`
     or equivalent fallback option in the schema itself wherever the
     original code has no safe default, since Jev cannot abstain on a
     forced choice.
   - **What changes and why**: one or two sentences — e.g. "the manual
     malformed-response fallback branch is removed because schema
     conformance is guaranteed; the confidence check stays because the
     schema guarantee is about shape, not correctness."
3. Present the full plan (all findings, both good- and poor-fit
   verdicts, and every before/after pair) to the user as a single message.

**STOP here. Do not proceed to Phase 3 until the user has explicitly
approved the plan**, or approved a specific subset of it. If the user
approves only some findings, only those go to Phase 3. If the user asks
for changes to the plan, revise and re-present it — don't execute a
revised plan without a fresh approval.

## Phase 3: Execute

Apply only the findings the user explicitly approved, one at a time.

1. For each approved finding, use the Edit tool to replace the "before"
   code with the "after" code from the approved plan — do not
   freelance a different implementation than what was shown to the user.
2. After each edit, briefly confirm what changed (file, function) before
   moving to the next approved finding.
3. If an edit turns out to need something the plan didn't anticipate
   (e.g. a new import, a client constructed elsewhere in the file), make
   the minimal necessary adjustment and say so — don't silently expand
   scope beyond what was approved.
4. Do not touch findings the user didn't approve, even if they look like
   easy wins.

## Phase 4: Validate

After executing the approved edits, validate the migrated decision
point(s) against Jev directly — don't just trust that the code compiles.

1. Build a `cases.json` file matching the exact schema in
   `scripts/sample_cases.json`: a JSON list of cases, each
   `{id, state, questions: {key: {type, instructions, criteria}},
   decision_key?, expected_decision?, model?}`. Derive cases from the
   executed change's existing test fixtures if the codebase has them;
   otherwise synthesize a small set of edge cases yourself (a clear
   positive, a clear negative, and at least one boundary/ambiguous case
   per migrated decision point). **Always set `expected_decision` on every
   case**, to the change's own expected/current behavior for that
   case — most users won't have `TYPESAFE_API_KEY` set, so the default run
   is simulated, and the script's simulated path just echoes
   `expected_decision` straight back as the decision; a case without it
   reports `"decision": "unknown"` and validates nothing.
2. Run the validator exactly as it's built to be called:
   ```
   python3 scripts/validate_with_jev.py --cases cases.json
   ```
   It prints `{"mode": "real"|"simulated", "results": [...]}` — `"real"`
   only when `TYPESAFE_API_KEY` is set in the environment and the call
   succeeded; otherwise it falls back to `"simulated"` automatically and
   labels every result accordingly.
3. **If any result carries a `schema_warnings` field, fix `cases.json`
   and re-run before reporting anything to the user.** The script attaches
   this per-case when a question's shape doesn't match the real API (wrong
   `type`, `options`/`min`/`max` used instead of `criteria`, empty
   `choice` criteria, or a `score` outside 2–10 levels) — it does not fail
   the run or change the exit code, so a clean-looking result can still
   carry one.
4. Report the results back to the user **verbatim**, including the
   top-level `mode` field. Never summarize a `simulated` run as if it
   were measured behavior — say plainly "this was simulated, not a real
   Jev call" whenever `mode` is `"simulated"`, and tell the user how to
   get a real run (`export TYPESAFE_API_KEY=...` and re-run) if they want
   one.

## Guardrails

- **Never execute an edit the user hasn't explicitly approved.** Phase 2's
  stop-and-approve gate is not optional, even for findings that look
  obviously correct.
- **Never present a simulated validation result as measured.** Always
  surface Phase 4's `mode` field as-is; a `simulated` result tells you the
  schema is well-formed, nothing about real-world accuracy.
- **Never invent Jev API details beyond what `references/` documents.**
  Where `references/integration-patterns.md` flags a shape as "not
  publicly confirmed" (e.g. some SDK accessor names, `TypeSafeClassifier`'s
  constructor), carry that uncertainty into the plan and prefer the
  confirmed generic REST fallback over a guessed convenience API.
- **A schema guarantee is not a correctness guarantee.** Jev "can't
  hallucinate" only means its output matches the declared type — the
  answer can still be wrong. Don't let a migration drop confidence checks
  or human-review fallbacks that existed for correctness reasons, not just
  parsing reasons.
