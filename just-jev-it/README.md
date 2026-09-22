# just-jev-it

## What it does

Audit an existing workflow, agent, automation, or codebase to find LLM call sites where TypeSafe AI's Jev model (a non-generative, typed-decision "System One" model) could replace or augment them, then plan, execute, and validate the migration. This skill works through four phases: **Audit** (find LLM calls and output-branching points), **Plan** (write before/after migration strategies with user approval gate), **Execute** (apply approved changes), and **Validate** (confirm against Jev with real or simulated runs).

## When it triggers

Use this skill when the user asks:
- "Can I use Jev for X?" or "Where could I use Jev in this repo?"
- They want to cut LLM cost/latency on classification, routing, triage, moderation, or confidence-gated decisions
- They explicitly say "just jev it" or invoke the skill by name

This skill audits *existing* code — not for designing a brand-new Jev integration from scratch (that greenfield task belongs to TypeSafe AI's own official "build with Jev" skill).

## What's inside

```
SKILL.md                    — The skill itself: the four-phase Audit → Plan → Execute → Validate
                               workflow an agent follows when invoked

references/
├── jev-overview.md         — What Jev is: its three typed question primitives (noul, choice, score),
│                             documented limitations, why it's not a drop-in LLM replacement
├── fit-heuristics.md       — Suitability test: what makes a good vs. poor Jev fit (decides vs.
│                             creates, predefined answer space, single focused judgment, etc.)
│                             with code signals and worked examples
└── integration-patterns.md — Replacement code shapes for Python SDK, LangChain chain, and
                             generic REST fallback across any framework/language

scripts/
├── sample_cases.json       — Template for cases.json validation format
│                             ({id, state, questions, decision_key, expected_decision, model})
└── validate_with_jev.py    — Phase 4 validator: runs cases against Jev, outputs
                             {"mode": "real"|"simulated"|"mixed", "results": [...]}

LICENSE.txt                 — MIT license text
```

## Validation

Phase 4 **Validation** distinguishes between two modes, reported per result and as a top-level aggregate:

- **Real mode** (`"mode": "real"`): Triggered when `TYPESAFE_API_KEY` is set in the environment and the Jev API call succeeds. Provides measured behavior against the real Jev service.
- **Simulated mode** (`"mode": "simulated"`): Default fallback when no API key is set or the call fails. The validator echoes back each case's `expected_decision` unchanged, validating only that the schema is well-formed — not real-world accuracy.

The top-level `mode` is `"real"` only if every case was real, `"simulated"` only if every case was simulated, and `"mixed"` if some of each happened in the same run (e.g. one case's call succeeded while another fell back after an error) — each result's own `mode` tells you which is which. Each result also carries `matches_expected` (true/false/null): whether the decision matched `expected_decision`, checked only for string-comparable `choice` answers — `null` for `noul`/`score` answers or cases with no `expected_decision`.

Always surface the `mode` field(s) in results. Never present a simulated run as measured behavior; tell the user how to get a real run (`export TYPESAFE_API_KEY=...` and re-run).

## Status

**This skill is new and unverified against the real Jev API.** Everything has been validated against Jev's documented behavior and simulated runs using the `validate_with_jev.py` script. A live validation against a real Jev account requires setting `TYPESAFE_API_KEY` in your environment and re-running Phase 4.
