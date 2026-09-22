# Toy workflow — just-jev-it smoke test

Throwaway sample used to smoke-test the finished `just-jev-it` skill
end-to-end against real code (Task 9 of
`docs/superpowers/plans/2026-09-22-just-jev-it-skill.md`). Not part of the
shipped skill.

`agent.py` started as a two-function toy support-ticket agent:
`classify_priority` (an LLM call re-parsed into a closed low/medium/high
enum) and `draft_reply` (a free-text LLM call). The skill's four phases were
run against it by an agent following `just-jev-it/SKILL.md` as its own
operating instructions (no live skill-registration system was available in
this environment).

## Result: PASS

| Phase | Outcome |
|---|---|
| 1. Audit | **Correct.** `classify_priority` flagged **good fit** (closed 3-way output space, defensive re-parse into an enum — the exact good-fit signal in `fit-heuristics.md`). `draft_reply` flagged **poor fit** (free text consumed by a human). Neither was misclassified; no fix to `fit-heuristics.md` was needed. |
| 2. Plan | Skill text genuinely requires stopping for approval ("**STOP here. Do not proceed to Phase 3 until the user has explicitly approved the plan**") — this is not optional language. A before/after plan was produced for `classify_priority` only, using the "plain Python agent loop" shape from `integration-patterns.md`. **Approval gate note:** since this is a controlled smoke test with no separate human present, the same agent played the approving-user role and self-approved the plan. This is a stand-in for real consent, not evidence the gate holds up against an independent second party — treat it as weaker signal than the other phases when judging pass/fail. |
| 3. Execute | **Correct.** Only `classify_priority` was edited, exactly to the approved "after" shape (`TypeSafeClient.system_one` with a `choice` question, `response.choices["priority"].choice` accessor). `draft_reply` is byte-for-byte unchanged from the original. |
| 4. Validate | `cases.json` built with 3 cases (clear low, clear high, one medium boundary case), each with `expected_decision` set per the skill's own instruction. `python3 just-jev-it/scripts/validate_with_jev.py --cases cases.json` was run for real (not simulated by description) and returned `"mode": "simulated"` (no `TYPESAFE_API_KEY` in this environment), each result echoing its `expected_decision` back as `decision` with a `SIMULATED` note, as documented. No `schema_warnings` appeared. Reported to the user as simulated, not measured, with the real-run instructions (`export TYPESAFE_API_KEY=...`). |

## Files here

- `agent.py` — toy workflow, post-migration (`classify_priority` migrated to
  Jev, `draft_reply` untouched).
- `cases.json` — validation cases for the migrated `classify_priority`
  decision point.

## Concerns / defects found

None in the skill's classification logic or phase mechanics — both
verdicts, the approval gate text, the execute-phase scoping, and the
validate-phase `simulated` handling all behaved as `SKILL.md` specifies.
The one caveat is procedural, not a skill defect: Phase 2's approval gate
could only be exercised by the same agent playing both roles in this test,
so this run demonstrates the skill *asks* for approval correctly, not that
a real second-party approval flow works — that needs a genuine multi-party
run to fully confirm. Separately, `agent.py`'s `classify_priority`/
`draft_reply` pair is verbatim identical to `fit-heuristics.md`'s own
Example 1/Example 2 worked examples, so this smoke test can't independently
catch a defect in those heuristics — it's testing the skill against its own
canonical example, not a case the heuristics haven't already seen.
