#!/usr/bin/env python3
"""Validate typed test cases against Jev (TypeSafe AI's System One model) —
makes a real API call if TYPESAFE_API_KEY is set, otherwise falls back to a
clearly-labeled simulation. Never reports simulated results as measured.

Request/response shapes follow the documented TypeSafe API
(https://docs.typesafe.ai/api), NOT the older placeholder shape some
third-party writeups show. Specifically:

  POST https://api.typesafe.ai/v1/systemone
  {"state": <state>, "model": "jev-1.13.0", "questions": {<key>: <Question>}}

Each Question is {"type": "noul"|"choice"|"score", "instructions": <str>,
"criteria": <shape depends on type>}:
  - noul:   criteria optional, {"true": <desc>, "false": <desc>}
  - choice: criteria REQUIRED, {<option>: <rubric>, ...} (up to 255 options)
  - score:  criteria REQUIRED, [<level 0 desc>, ..., <level N desc>] (2-10 levels)

Response: {"model": <str>, "answers": {<key>: <Answer>}, "usage": {...}}.
Each Answer's shape depends on the question type:
  - noul:   {"noul": <0-1 float>}
  - choice: {"choice": <str>, "probabilities": {...}, "confidence": <0-1 float>}
  - score:  {"score": <float>, "legend": {...}, "probabilities": {...}, "confidence": <0-1 float>}

A third-party guide (DataCamp) has been observed showing an incorrect,
non-official shape using "options"/"min"/"max" fields instead of "criteria".
This script flags that shape as invalid rather than silently accepting it.

Each result carries its own "mode" ("real" or "simulated") in addition to
the top-level aggregate "mode" ("real" only if every case was real,
"simulated" only if every case was simulated, "mixed" otherwise), and a
"matches_expected" field: True/False when the case has an
"expected_decision" and the decision is a directly string-comparable
"choice" answer, or None (not checked) when there's no "expected_decision"
or the decision is a "noul"/"score" float.
"""
import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error

API_KEY_ENV = "TYPESAFE_API_KEY"
API_URL = os.environ.get("TYPESAFE_API_URL", "https://api.typesafe.ai/v1/systemone")
# Pin the model version rather than tracking "jev-latest", per TypeSafe's own
# guidance, to avoid silent calibration drift between runs.
DEFAULT_MODEL = os.environ.get("TYPESAFE_MODEL", "jev-1.13.0")

VALID_QUESTION_TYPES = {"noul", "choice", "score"}


def validate_question_schema(key, question):
    """Return a list of schema-violation warning strings for one Question.

    Catches the known incorrect shape (options/min/max fields) reported in
    third-party writeups, which does not match the official TypeSafe API
    reference (criteria-only).
    """
    warnings = []
    qtype = question.get("type")
    if qtype not in VALID_QUESTION_TYPES:
        warnings.append(
            f"question '{key}': type {qtype!r} is not one of {sorted(VALID_QUESTION_TYPES)}"
        )
    if "options" in question or "min" in question or "max" in question:
        warnings.append(
            f"question '{key}': found 'options'/'min'/'max' field(s) — this does not match "
            "the official TypeSafe API, which uses 'criteria' only (a map for 'choice', "
            "a 2-10 item ordered array for 'score'). Fix the case file."
        )
    criteria = question.get("criteria")
    if qtype == "choice":
        if not isinstance(criteria, dict) or not criteria:
            warnings.append(f"question '{key}': type 'choice' requires a non-empty criteria map")
        elif len(criteria) > 255:
            warnings.append(f"question '{key}': 'choice' criteria has >255 options")
    elif qtype == "score":
        if not isinstance(criteria, list) or not (2 <= len(criteria) <= 10):
            warnings.append(
                f"question '{key}': type 'score' requires a criteria array with 2-10 ordered levels"
            )
    return warnings


def validate_case_schema(case):
    warnings = []
    questions = case.get("questions", {})
    if not isinstance(questions, dict):
        warnings.append(
            f"case {case.get('id')!r}: 'questions' must be a map of {{key: Question}}, "
            f"got {type(questions).__name__}"
        )
        return warnings
    for key, question in questions.items():
        warnings.extend(validate_question_schema(key, question))
    return warnings


def extract_decision(case, answers):
    """Reduce a (possibly multi-question) answers map to one (decision,
    confidence) pair for the case-level summary, per the answer shape for
    the relevant question's type."""
    decision_key = case.get("decision_key")
    if decision_key is None:
        questions = case.get("questions", {})
        decision_key = next(iter(questions), None)

    if decision_key is None or decision_key not in answers:
        return None, None

    answer = answers[decision_key]
    if "choice" in answer:
        return answer["choice"], answer.get("confidence")
    if "score" in answer:
        return answer["score"], answer.get("confidence")
    if "noul" in answer:
        # noul answers carry only a probability, no separate confidence field.
        return answer["noul"], None
    return None, None


def compute_matches_expected(case, decision):
    """Compare `decision` to the case's `expected_decision`.

    Returns True/False when there's an `expected_decision` to compare
    against AND `decision` is directly string-comparable (a `choice`
    answer). Returns None (not checked) when there's no `expected_decision`,
    or when `decision` is a `noul`/`score` float that isn't a like-for-like
    string comparison — reported honestly as "not checked" rather than
    inventing a fuzzy-match heuristic for numeric answers.
    """
    expected = case.get("expected_decision")
    if expected is None:
        return None
    if isinstance(decision, str) and isinstance(expected, str):
        return decision == expected
    return None


# Per TypeSafe's documented API guidance: 429 (rate limit) and 529 (service
# overloaded) should be retried with exponential backoff; the official SDKs
# do this automatically. This is a lightweight validation script, not a
# production client, so we keep it to a couple of short, fixed-backoff
# retries rather than a full retry framework.
RETRYABLE_STATUS_CODES = {429, 529}
MAX_RETRIES = 2
BACKOFF_SECONDS = 1.5


def call_real_api(case, api_key):
    payload = json.dumps({
        "state": case["state"],
        "model": case.get("model", DEFAULT_MODEL),
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

    attempt = 0
    while True:
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            if exc.code in RETRYABLE_STATUS_CODES and attempt < MAX_RETRIES:
                attempt += 1
                time.sleep(BACKOFF_SECONDS * attempt)
                continue
            raise

    answers = body.get("answers", {})
    decision, confidence = extract_decision(case, answers)
    return {
        "decision": decision,
        "confidence": confidence,
        "model": body.get("model"),
        "answers": answers,
        "usage": body.get("usage"),
    }


def simulate(case, note="SIMULATED - no TYPESAFE_API_KEY set, not a real Jev call"):
    return {
        "decision": case.get("expected_decision", "unknown"),
        "confidence": None,
        "note": note,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--cases",
        required=True,
        help="Path to a JSON file: list of cases, each "
        "{id, state, questions: {key: Question}, decision_key?, expected_decision?, model?}",
    )
    args = parser.parse_args()

    try:
        with open(args.cases) as f:
            cases = json.load(f)
    except OSError as exc:
        print(f"Error: could not read cases file '{args.cases}': {exc}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"Error: could not parse cases file '{args.cases}' as JSON: {exc}", file=sys.stderr)
        return 1

    api_key = os.environ.get(API_KEY_ENV)
    results = []
    result_modes = []

    for case in cases:
        schema_warnings = validate_case_schema(case)
        # Per-result mode: "real" only if this specific case's call actually
        # reached the live API; falls back to "simulated" below on any
        # exception, independent of how other cases in this run fared.
        result_mode = "real" if api_key else "simulated"

        try:
            if api_key:
                outcome = call_real_api(case, api_key)
            else:
                outcome = simulate(case)
        except urllib.error.URLError as exc:
            # Covers HTTPError too (it subclasses URLError) — network errors,
            # non-2xx responses (including 429/529 once retries in
            # call_real_api are exhausted), and connection failures.
            outcome = simulate(
                case,
                note=f"SIMULATED - real API call failed ({exc}), falling back to simulation",
            )
            outcome["error"] = str(exc)
            result_mode = "simulated"
        except (KeyError, json.JSONDecodeError) as exc:
            # A malformed case (missing "state"/"questions") or an
            # unexpected non-JSON/malformed response body should degrade
            # this one case to simulation rather than crash the whole run.
            outcome = simulate(
                case,
                note=f"SIMULATED - malformed case or response ({exc!r}), falling back to simulation",
            )
            outcome["error"] = repr(exc)
            result_mode = "simulated"

        outcome["matches_expected"] = compute_matches_expected(case, outcome.get("decision"))

        if schema_warnings:
            outcome["schema_warnings"] = schema_warnings

        outcome["mode"] = result_mode
        result_modes.append(result_mode)
        results.append({"case_id": case.get("id"), **outcome})

    # Aggregate mode: "real" only if every case's call was real, "simulated"
    # only if every case's call was simulated, "mixed" otherwise. An empty
    # case list falls back to what the environment alone implies.
    if not result_modes:
        aggregate_mode = "real" if api_key else "simulated"
    elif all(m == "real" for m in result_modes):
        aggregate_mode = "real"
    elif all(m == "simulated" for m in result_modes):
        aggregate_mode = "simulated"
    else:
        aggregate_mode = "mixed"

    print(json.dumps({"mode": aggregate_mode, "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
