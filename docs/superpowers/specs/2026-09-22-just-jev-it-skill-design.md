# just-jev-it — Skill Design

## Purpose

A Claude Code skill that audits a user's existing workflow, automation, or
agent, determines which decision points could be replaced or augmented by
Jev (TypeSafe AI's "System One" model), proposes a concrete migration plan,
executes it on approval, and validates the result — against the real Jev API
when credentials are available, otherwise via a clearly-labeled simulation.

Target distribution: a PR to `anthropics/skills` (public community skills
repo), following that repo's `SKILL.md` + `references/` + `scripts/`
conventions.

## Background: what Jev is

Jev is a non-generative "System One" model from TypeSafe AI (announced
2026-09-15). It does not produce text: it takes a block of state plus a set
of typed questions and returns calibrated probabilistic decisions in
parallel. Because outputs are constrained to pre-declared types, it cannot
hallucinate in the way an LLM can. TypeSafe claims large speed/cost
advantages (~193x faster, ~445x cheaper) over frontier LLMs for
decision-shaped tasks specifically — not for open-ended generation.

This makes Jev a fit for the *decision/classification/routing* slice of a
workflow, not the *generation* slice. The skill's job is to tell those two
slices apart in a given codebase and recommend accordingly.

## Package layout

```
just-jev-it/
  SKILL.md                    # orchestrates audit -> plan -> execute -> validate
  references/
    jev-overview.md           # what Jev is, API shape, pricing, limits (cited)
    fit-heuristics.md         # patterns that are/aren't a good Jev fit, with examples
    integration-patterns.md   # wiring Jev into common agent frameworks
  scripts/
    validate_with_jev.py      # real API call if key present, else simulate + label
  README.md                   # PR-facing description
```

## SKILL.md — phases

One skill, single entry point, four internal phases:

1. **Audit** — read the target codebase/workflow. Find LLM call sites,
   prompt templates, and code that branches on an LLM's output
   (classification, routing, approval gates, confidence thresholds). Classify
   each as jev-fit / not-a-fit using `fit-heuristics.md`, with a one-line
   reason per finding.
2. **Plan** — for each jev-fit finding, write a concrete before/after: what
   typed schema (inputs, typed question set, output type) replaces the
   prompt; what accuracy/behavior risk exists; what stays on the LLM. This is
   presented to the user before any code changes.
3. **Execute** — only after explicit user approval of the plan, apply edits
   swapping in typed Jev calls where flagged. No silent execution.
4. **Validate** — derive test cases from existing code paths / fixtures.
   Run them through `scripts/validate_with_jev.py`. If a Jev/TypeSafe API key
   env var is present, this is a real call and results are reported as
   measured. If absent, results are explicitly labeled as a simulated
   estimate based on documented Jev behavior — never presented as measured.

## Research inputs (built before the skill, not guessed)

- Deep research pass (dispatched to Opus) on Jev/TypeSafe AI: real API
  shape, documented use cases, accuracy/calibration claims, limitations,
  pricing, and integration patterns with common agent frameworks — all
  cited to sources, feeding `references/`.
- A pass (dispatched to Sonnet, using the `anthropic-skills:skill-creator`
  skill) to confirm the exact `SKILL.md` format and conventions the
  `anthropics/skills` repo expects, rather than assuming.

## Testing

Before any GitHub submission: build a small sample workflow (a toy agent
with an obvious classification/routing step and an obvious generation step)
and run the finished skill against it end-to-end, confirming it correctly
flags the routing step as jev-fit, leaves the generation step alone, and
that the validate phase's simulation-vs-real labeling is accurate.

## Out of scope

- Actually opening the GitHub PR without explicit user confirmation.
- Building a real TypeSafe AI account/integration test harness beyond what
  public docs support.
