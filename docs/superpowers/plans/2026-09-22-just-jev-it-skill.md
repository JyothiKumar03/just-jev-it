# just-jev-it Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `just-jev-it` Claude Code skill — audits a workflow/agent/automation, flags decision points that fit TypeSafe AI's Jev model, plans and executes the swap on approval, and validates against the real Jev API when available (else a clearly-labeled simulation) — ready for submission to `anthropics/skills`.

**Architecture:** One skill (`SKILL.md`) with four in-instruction phases (audit → plan → execute → validate), backed by three bundled reference docs the skill reads for domain knowledge, and one Python validation script that calls the real Jev API when a key is present and otherwise simulates with an explicit label.

**Tech Stack:** Markdown (SKILL.md + references), Python 3 stdlib only for `scripts/validate_with_jev.py` (no new dependency — use `urllib.request`, not `requests`, so the script runs with zero install).

**Spec:** `docs/superpowers/specs/2026-09-22-just-jev-it-skill-design.md`

## Global Constraints

- Every factual claim about Jev/TypeSafe AI in `references/` must carry a source URL — no invented specifics (endpoints, pricing numbers, benchmark figures) beyond what a cited source states.
- `SKILL.md` frontmatter must have exactly `name` and `description` fields per the `anthropics/skills` template, `name: just-jev-it`.
- Nothing in this plan opens a GitHub PR or pushes to a remote — that stays a separate, explicitly-confirmed step after this plan is done.
- No new runtime dependency: `scripts/validate_with_jev.py` uses only the Python stdlib.

---

### Task 1: Research Jev/TypeSafe AI (dispatch to an Opus agent)

**Files:**
- Create: `docs/superpowers/plans/artifacts/jev-research.md` (raw research output, cited)

**Interfaces:**
- Produces: a markdown research doc with these exact sections, each populated with cited facts (URL per claim) — later tasks (3, 4, 5) consume this directly:
  - `## What Jev Is` — architecture category (System One / non-generative), how it differs mechanically from an LLM call
  - `## API / Integration Shape` — what a call looks like (inputs: state block + typed questions; outputs: calibrated decisions), auth model, SDKs/languages supported, based on TypeSafe's own docs/blog if reachable, otherwise clearly marked "not publicly documented as of research date"
  - `## Documented and Speculative Use Cases` — split into two subsections: "confirmed in a published source" vs "plausible extrapolation" (clearly labeled which is which) — routing/classification, moderation gates, fraud/risk scoring, approval workflows, agent tool-selection, feature flagging, A/B decisioning, retry/escalation logic, and any others found
  - `## Performance & Cost Claims` — the speed/cost multipliers as published, with source, and any independent benchmarks found
  - `## Limitations` — what it explicitly cannot do (no free text generation, needs pre-declared output types, anything about training/calibration data requirements)
  - `## Sources` — full list of URLs used

- [ ] **Step 1: Dispatch research agent**

Use the Agent tool with `subagent_type: "general-purpose"` and `model: "opus"`. Prompt must include: the goal above, the exact section list, the instruction that every claim needs a source URL, and that "speculative" use cases must be explicitly labeled as such and not blended with confirmed ones. Give it the four sources already gathered this session (TechCrunch, Tom's Hardware, TypeSafe AI blog, DataCamp URLs) as a starting point and tell it to go further (TypeSafe's own docs site, any GitHub/SDK repo, Hacker News discussion for practitioner-reported use cases).

- [ ] **Step 2: Save the agent's output**

Write the returned research content to `docs/superpowers/plans/artifacts/jev-research.md`.

- [ ] **Step 3: Verify no placeholder/uncited claims**

Read the file back. Confirm every bullet under "Documented and Speculative Use Cases" and every number under "Performance & Cost Claims" has an adjacent URL or is explicitly under the "speculative" subsection. If any claim lacks a source, either find one or move it to speculative.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/artifacts/jev-research.md
git commit -m "Add Jev/TypeSafe AI research for just-jev-it skill"
```

---

### Task 2: Confirm anthropics/skills SKILL.md conventions (dispatch to a Sonnet agent using skill-creator)

**Files:**
- Create: `docs/superpowers/plans/artifacts/skill-format-notes.md`

**Interfaces:**
- Produces: a short markdown doc with these sections, consumed by Tasks 6 and 7:
  - `## Required frontmatter` — exact fields and constraints (name pattern, description length/style guidance)
  - `## Directory conventions` — when to use `references/`, `scripts/`, `assets/`, how the skill body should reference them (relative paths, on-demand loading language)
  - `## Style rules` — voice/format conventions the `anthropics/skills` examples follow (imperative instructions, section headers used, example/guideline sections)
  - `## Checklist` — a submission checklist (what `anthropics/skills` reviewers look for) if discoverable, else "not found publicly — using template + spec only"

- [ ] **Step 1: Dispatch format-research agent**

Use the Agent tool, `subagent_type: "general-purpose"` (default Sonnet). Prompt: invoke the `anthropic-skills:skill-creator` skill and follow its guidance to determine the canonical `SKILL.md` format; also fetch `https://github.com/anthropics/skills` template and spec directories and at least one real example skill (e.g. the `docx` or `pdf` skill) to observe real conventions in practice. Report back in the exact section structure above.

- [ ] **Step 2: Save the output**

Write to `docs/superpowers/plans/artifacts/skill-format-notes.md`.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/plans/artifacts/skill-format-notes.md
git commit -m "Add skill-format research for just-jev-it skill"
```

---

### Task 3: Write `references/jev-overview.md`

**Files:**
- Create: `just-jev-it/references/jev-overview.md`

**Interfaces:**
- Consumes: `docs/superpowers/plans/artifacts/jev-research.md` (Task 1)
- Produces: a reference file `SKILL.md` (Task 7) will point to for "what is Jev" background — must be skimmable, not a dump of the raw research.

- [ ] **Step 1: Draft the file**

Condense `jev-research.md`'s "What Jev Is", "API / Integration Shape", "Performance & Cost Claims", and "Limitations" sections into a single skimmable reference (headings, short paragraphs/bullets, keep source URLs as a `## Sources` footer). Target under 200 lines.

- [ ] **Step 2: Verify against source**

Diff-check by eye: every specific number or claim in the drafted file must trace back to something in `jev-research.md`. Remove anything that doesn't.

- [ ] **Step 3: Commit**

```bash
git add just-jev-it/references/jev-overview.md
git commit -m "Add Jev overview reference to just-jev-it skill"
```

---

### Task 4: Write `references/fit-heuristics.md`

**Files:**
- Create: `just-jev-it/references/fit-heuristics.md`

**Interfaces:**
- Consumes: `docs/superpowers/plans/artifacts/jev-research.md` (Task 1, "Documented and Speculative Use Cases" + "Limitations" sections)
- Produces: the heuristics the SKILL.md audit phase applies to each LLM call site it finds. Must be concrete enough to pattern-match against code, not abstract advice.

- [ ] **Step 1: Draft the heuristics table**

Write a `## Good Jev Fit` section and a `## Poor Jev Fit` section, each as a table or bullet list of concrete code-shaped signals, e.g.:
  - Good fit: an LLM call whose prompt ends in "answer yes/no", "pick one of: A/B/C", "rate confidence 0-1", "classify as X/Y/Z" — i.e. the prompt already declares a closed output space.
  - Good fit: `if llm_response in [...]:` / regex-parsing an LLM's free-text answer into an enum — the parsing itself signals the output was always meant to be typed.
  - Poor fit: prompts producing free text consumed by a human (summaries, drafts, chat replies) or fed into another LLM prompt as unstructured context.
  - Poor fit: multi-turn conversational state where the "decision" depends on open-ended prior dialogue Jev's typed-question model doesn't capture.
  For each entry, note which part of `jev-research.md` supports it.

- [ ] **Step 2: Add worked examples**

Include 2-3 short before/after code snippets (pseudocode, framework-agnostic) showing a flagged decision point and its typed-schema replacement sketch.

- [ ] **Step 3: Commit**

```bash
git add just-jev-it/references/fit-heuristics.md
git commit -m "Add fit-heuristics reference to just-jev-it skill"
```

---

### Task 5: Write `references/integration-patterns.md`

**Files:**
- Create: `just-jev-it/references/integration-patterns.md`

**Interfaces:**
- Consumes: `docs/superpowers/plans/artifacts/jev-research.md` (Task 1, "API / Integration Shape")
- Produces: patterns the SKILL.md execute phase follows when writing actual replacement code, keyed by common agent-framework shapes.

- [ ] **Step 1: Draft framework sections**

One short section each for: plain Python agent loop, LangChain-style tool/chain, and a generic "any framework with an LLM classification call" fallback pattern. Each section shows the typed-schema call shape from `jev-overview.md`'s API section, wired in as a drop-in replacement for a classification/routing call.

- [ ] **Step 2: Mark unknowns explicitly**

Anywhere the real Jev SDK/client shape isn't confirmed by research, write the snippet as illustrative pseudocode with a visible `# shape not publicly confirmed — verify against TypeSafe docs before use` comment rather than inventing a fake API.

- [ ] **Step 3: Commit**

```bash
git add just-jev-it/references/integration-patterns.md
git commit -m "Add integration-patterns reference to just-jev-it skill"
```

---

### Task 6: Write `scripts/validate_with_jev.py`

**Files:**
- Create: `just-jev-it/scripts/validate_with_jev.py`

**Interfaces:**
- Consumes: env var `TYPESAFE_API_KEY` (or documented equivalent from `jev-overview.md`'s API section — use whatever name the research confirms; default to `TYPESAFE_API_KEY` if unconfirmed)
- Produces: a CLI the SKILL.md validate phase invokes: `python3 validate_with_jev.py --cases cases.json` → prints JSON to stdout: `{"mode": "real"|"simulated", "results": [{"case_id": ..., "decision": ..., "confidence": ...}]}`

- [ ] **Step 1: Write the script**

```python
#!/usr/bin/env python3
"""Validate typed test cases against Jev — real API call if a key is
present, otherwise a labeled simulation. Never reports simulated results
as measured."""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

API_KEY_ENV = "TYPESAFE_API_KEY"
API_URL = os.environ.get("TYPESAFE_API_URL", "https://api.typesafe.ai/v1/jev/decide")


def call_real_api(case, api_key):
    payload = json.dumps({
        "state": case["state"],
        "questions": case["questions"],
    }).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def simulate(case):
    return {
        "decision": case.get("expected_decision", "unknown"),
        "confidence": None,
        "note": "SIMULATED - no TYPESAFE_API_KEY set, not a real Jev call",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", required=True, help="Path to a JSON file: list of {id, state, questions, expected_decision}")
    args = parser.parse_args()

    with open(args.cases) as f:
        cases = json.load(f)

    api_key = os.environ.get(API_KEY_ENV)
    mode = "real" if api_key else "simulated"
    results = []

    for case in cases:
        try:
            if api_key:
                outcome = call_real_api(case, api_key)
            else:
                outcome = simulate(case)
        except urllib.error.URLError as exc:
            outcome = {"error": str(exc), "note": "API call failed, falling back to simulation"}
            outcome.update(simulate(case))
            mode = "simulated"
        results.append({"case_id": case.get("id"), **outcome})

    print(json.dumps({"mode": mode, "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Create a sample cases file for smoke testing**

Create `just-jev-it/scripts/sample_cases.json`:
```json
[
  {
    "id": "case-1",
    "state": {"order_total": 42.50, "customer_risk_score": 0.1},
    "questions": ["should_auto_approve"],
    "expected_decision": "approve"
  },
  {
    "id": "case-2",
    "state": {"order_total": 9999.00, "customer_risk_score": 0.8},
    "questions": ["should_auto_approve"],
    "expected_decision": "reject"
  }
]
```

- [ ] **Step 3: Run it with no API key set and verify simulated mode**

Run: `cd just-jev-it/scripts && python3 validate_with_jev.py --cases sample_cases.json`
Expected: JSON output with `"mode": "simulated"`, two results, each with a `"note"` field saying it's simulated. Confirm no crash and no real network call is attempted when the key is absent (read the code path — `api_key` is falsy so `call_real_api` is never called).

- [ ] **Step 4: Commit**

```bash
git add just-jev-it/scripts/validate_with_jev.py just-jev-it/scripts/sample_cases.json
git commit -m "Add validate_with_jev.py script to just-jev-it skill"
```

---

### Task 7: Write `SKILL.md`

**Files:**
- Create: `just-jev-it/SKILL.md`

**Interfaces:**
- Consumes: `docs/superpowers/plans/artifacts/skill-format-notes.md` (Task 2, for exact frontmatter/style conventions) and the three files under `just-jev-it/references/` (Tasks 3-5) and `just-jev-it/scripts/validate_with_jev.py` (Task 6) by relative path
- Produces: the complete, invokable skill.

- [ ] **Step 1: Write frontmatter matching Task 2's confirmed conventions**

```yaml
---
name: just-jev-it
description: Audit an existing workflow, automation, or agent to determine whether TypeSafe AI's Jev model (a non-generative, typed-decision "System One" model) can replace or augment its LLM-based decision points. Produces a fit report, a migration plan, executes approved changes, and validates with real or simulated Jev calls. Use when the user asks "can I use Jev for X", wants to reduce LLM cost/latency on classification or routing steps, or explicitly invokes just-jev-it.
---
```
Adjust field names/style exactly per `skill-format-notes.md` if it specifies something different.

- [ ] **Step 2: Write the four-phase instructions body**

Body must include, as literal instructions Claude follows when the skill is active:
- An opening paragraph stating the skill's purpose and pointing to `references/jev-overview.md` for background (read it first).
- `## Phase 1: Audit` — instructs Claude to Grep/Read the target for LLM call sites and output-branching code, classify each using `references/fit-heuristics.md`, and produce a findings table (file:line, snippet, verdict, one-line reason).
- `## Phase 2: Plan` — instructs Claude to write a before/after plan per jev-fit finding using `references/integration-patterns.md` for the replacement shape, and present it to the user; explicitly instructs Claude to STOP and get explicit approval before Phase 3.
- `## Phase 3: Execute` — instructs Claude to apply only the approved edits, one finding at a time, using the Edit tool.
- `## Phase 4: Validate` — instructs Claude to derive a `cases.json` (same shape as `scripts/sample_cases.json`) from the executed change's test fixtures or from synthesized edge cases if none exist, run `python3 scripts/validate_with_jev.py --cases cases.json`, and report results verbatim including the `mode` field so the user always knows real vs simulated.
- A closing `## Guardrails` section: never execute without approval; never present simulated validation results as measured; never invent Jev API details beyond what `references/` documents.

- [ ] **Step 3: Verify internal links resolve**

Confirm every `references/...` and `scripts/...` path mentioned in `SKILL.md` exists on disk (`ls just-jev-it/references just-jev-it/scripts`).

- [ ] **Step 4: Commit**

```bash
git add just-jev-it/SKILL.md
git commit -m "Add SKILL.md for just-jev-it skill"
```

---

### Task 8: Write `README.md` (PR-facing)

**Files:**
- Create: `just-jev-it/README.md`

**Interfaces:**
- Consumes: nothing new — summarizes Tasks 1-7's output for a human reader browsing the repo/PR.

- [ ] **Step 1: Write the README**

Sections: `## What it does` (2-3 sentences), `## When it triggers`, `## What's inside` (file tree with one-line purpose each), `## Validation` (explain real-vs-simulated mode), `## Status` (note this is new/unverified against the real Jev API pending a live key).

- [ ] **Step 2: Commit**

```bash
git add just-jev-it/README.md
git commit -m "Add README for just-jev-it skill"
```

---

### Task 9: End-to-end smoke test against a toy workflow

**Files:**
- Create: `docs/superpowers/plans/artifacts/toy-workflow/agent.py` (throwaway sample, not part of the shipped skill)
- Create: `docs/superpowers/plans/artifacts/toy-workflow/README.md` (what it is)

**Interfaces:**
- Consumes: the finished `just-jev-it` skill (Tasks 3-7)
- Produces: a recorded pass/fail note confirming the skill behaves correctly end-to-end.

- [ ] **Step 1: Write a toy agent with one obvious classification call and one obvious generation call**

```python
"""Toy support-ticket agent for smoke-testing just-jev-it."""

def classify_priority(ticket_text, llm):
    """Classify a ticket's priority as low/medium/high using an LLM prompt."""
    prompt = f"Classify this ticket's priority as low, medium, or high:\n{ticket_text}\nAnswer with one word."
    response = llm.complete(prompt)
    if response.strip().lower() not in {"low", "medium", "high"}:
        return "medium"
    return response.strip().lower()


def draft_reply(ticket_text, llm):
    """Draft a free-text reply to the customer. Not a classification task."""
    prompt = f"Write a helpful, empathetic reply to this support ticket:\n{ticket_text}"
    return llm.complete(prompt)
```

- [ ] **Step 2: Invoke the just-jev-it skill against this file**

In a Claude Code session with the skill installed, ask: "just-jev-it this file" pointing at `docs/superpowers/plans/artifacts/toy-workflow/agent.py`. Let it run Phase 1 (Audit).

- [ ] **Step 3: Verify the audit result**

Confirm the audit findings table flags `classify_priority` as jev-fit (closed 3-way output space, already parsed into an enum) and `draft_reply` as poor-fit (free text). If either is misclassified, fix `references/fit-heuristics.md` (Task 4) and re-run.

- [ ] **Step 4: Verify the plan phase stops for approval**

Confirm Phase 2 produces a plan and explicitly asks for approval rather than editing immediately. Approve it.

- [ ] **Step 5: Verify execute + validate**

Confirm Phase 3 edits only `classify_priority`, leaves `draft_reply` untouched, and Phase 4 runs `validate_with_jev.py` and reports `"mode": "simulated"` (no real key in this environment) without claiming a measured result.

- [ ] **Step 6: Record the outcome and commit**

Write a short pass/fail note into `docs/superpowers/plans/artifacts/toy-workflow/README.md`, then:
```bash
git add docs/superpowers/plans/artifacts/toy-workflow
git commit -m "Add toy-workflow smoke test for just-jev-it skill"
```

---

### Task 10: Final self-review and PR readiness

**Files:**
- Modify: none (review only)

**Interfaces:**
- Consumes: everything from Tasks 1-9

- [ ] **Step 1: Re-read `just-jev-it/SKILL.md` and all `references/` files fresh**

Check for: any remaining "TBD"/placeholder text, any uncited specific claim about Jev, any broken relative path.

- [ ] **Step 2: Confirm scope boundary**

Confirm nothing in `just-jev-it/` attempts network calls except `scripts/validate_with_jev.py`, and that it only does so with an explicit API key present.

- [ ] **Step 3: Report readiness to the user**

Summarize what was built, the smoke-test result from Task 9, and explicitly ask whether to proceed to opening a PR against `anthropics/skills` — do not open it without that explicit go-ahead.
