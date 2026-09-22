# Integration Patterns

How to wire a typed Jev call into an existing codebase during the EXECUTE
phase, once `fit-heuristics.md` has confirmed a decision point is a good
Jev candidate. Every confirmed shape here traces to
`docs/superpowers/plans/artifacts/jev-research.md` ("API / Integration
Shape") or the condensed `jev-overview.md`. Anywhere the research doesn't
confirm a detail, the snippet says so explicitly and should not be written
into a user's repo as-is without verifying against `docs.typesafe.ai` first.

## Core call shape (recap)

Every Jev call needs a `state` (what's being judged), a `model`, and a
`questions` map keyed by caller-chosen names. Official SDKs read the API
key from `TYPESAFE_API_KEY` and construct the client as a context manager
(Python) or a plain instance (JS) — see `jev-research.md`, "Official SDKs
and repos," Python and TypeScript examples.

```
POST https://api.typesafe.ai/v1/systemone
{ "state": ..., "model": "jev-1.13.0", "questions": { "<key>": {type, instructions, criteria} } }
→ { "model", "answers": {"<key>": <Answer>}, "usage" }
```

**Response-access gotcha — read this before writing any "after" code.** The
raw REST envelope and the TypeScript SDK both use a flat `answers` map
(`response.answers.category.choice`, per `jev-research.md`'s TypeScript
example). The **Python SDK does not mirror this** — its README example
accesses `response.choices["category"].choice`, and the Langfuse `noul`
example accesses `result.nouls["user_disagreement"].noul` — i.e. the Python
client appears to expose per-type accessor properties (`.choices`,
`.nouls`, and presumably `.scores` by analogy) rather than a single
`.answers` dict.

```
# shape not publicly confirmed — verify against TypeSafe docs before use
# `.scores["<key>"].score` for `score`-type questions is inferred by analogy
# with `.choices`/`.nouls`; jev-research.md's official Python README example
# only demonstrates `.choices`, and the Langfuse example only `.nouls`.
```

Don't mix the two conventions when writing a migration: Python code uses
`.choices["<key>"]` / `.nouls["<key>"]`; JS/TS code and raw HTTP responses
use `.answers.<key>` / `["answers"]["<key>"]`.

---

## (a) Plain Python agent loop

A typical agent loop has a decision point — "what should happen next" —
answered today by asking an LLM for one of a small set of words and
re-parsing the reply. This is the classic good-fit shape from
`fit-heuristics.md` (closed output space, re-parsed into an enum,
drives `if`/`elif` control flow).

**Before:**

```python
def decide_next_action(agent_state, llm):
    prompt = (
        f"Given the current state: {agent_state}\n"
        "What should happen next? Answer with exactly one of: "
        "continue, retry, escalate, done."
    )
    response = llm.complete(prompt)
    action = response.strip().lower()
    if action not in {"continue", "retry", "escalate", "done"}:
        action = "escalate"  # fallback for a malformed LLM answer
    return action
```

**After** — real SDK construction pattern
(`with TypeSafeClient() as client:`), `Choice(instructions=..., criteria=...)`,
and `response.choices["key"].choice` access, all per
`jev-research.md`'s official Python README example:

```python
from typesafe_sdk import Choice, TypeSafeClient

def decide_next_action(agent_state, client: TypeSafeClient):
    response = client.system_one(
        state={"agent_state": agent_state},
        questions={
            "next_action": Choice(
                instructions="What should the agent do next, given its current state?",
                criteria={
                    "continue": "Keep executing the current plan; no blocker",
                    "retry": "The last step failed transiently and should be retried",
                    "escalate": "Blocked, risky, or ambiguous — a human should decide",
                    "done": "The task is complete",
                },
            ),
        },
    )
    answer = response.choices["next_action"]
    # `.choice` access is directly confirmed by jev-research.md's official
    # Python README example. `.confidence` as a Python attribute (rather
    # than `["confidence"]`) is inferred from the documented Answer JSON
    # schema (choice answers carry a `confidence` field) plus the SDK's
    # typed-accessor pattern — not directly shown in a Python code example
    # in the research. Verify the exact attribute name against the current
    # SDK before relying on it.
    if answer.confidence < 0.5:
        return "escalate"  # low-confidence answers shouldn't drive the loop
    return answer.choice

# Open the client once for the lifetime of the loop, not once per decision —
# it's a context manager tied to a connection, matching the README's
# `with TypeSafeClient() as client:` usage. Pin the model version per the
# pre-production checklist rather than tracking `jev-latest`.
with TypeSafeClient(model="jev-1.13.0") as client:
    while not done:
        action = decide_next_action(agent_state, client)
        agent_state, done = apply_action(action, agent_state)
```

The manual `if action not in {...}` fallback disappears — schema
conformance is guaranteed — but the confidence check stays: the schema
guarantee is about *shape*, not correctness (`jev-research.md`, "'Can't
hallucinate' — what it actually means"), and confidence-gated routing is
Jev's own documented pattern (`jev-research.md`, "Officially documented
architectural patterns" #2).

---

## (b) LangChain-style tool/chain

`jev-research.md` confirms LangChain ships an integration —
`TypeSafeClassifier`, which "accept[s] text, structured data, or LangChain
messages" as state (`jev-research.md`, "Third-party / ecosystem integration
surfaces" — LangChain). That's the extent of what the research confirms:
the class name and what it accepts as state. The constructor's other
arguments, how questions are defined on it, and its output shape are **not**
confirmed by any source in `jev-research.md`.

**Before** — a LangChain classification chain built on a general LLM:

```python
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

classify_prompt = PromptTemplate.from_template(
    "Classify this support message as billing, technical, or account:\n"
    "{message}\nRespond with exactly one word."
)
chain = LLMChain(llm=ChatOpenAI(), prompt=classify_prompt)
category = chain.run(message=ticket_text).strip().lower()
```

**After, option 1 — `TypeSafeClassifier`** (real class name and state
handling per `jev-research.md`; everything else is illustrative):

```python
# CONFIRMED (jev-research.md, "Third-party / ecosystem integration surfaces"):
# LangChain ships `TypeSafeClassifier`, which accepts text, structured data,
# or LangChain messages as state.
# shape not publicly confirmed — verify against TypeSafe docs before use
# (constructor args, question-definition API, and result shape below are
# illustrative, modeled on the confirmed core API's `Choice`/`criteria`
# shape — NOT verified against LangChain's actual TypeSafeClassifier docs)
from langchain_typesafe import TypeSafeClassifier  # package path unconfirmed

classifier = TypeSafeClassifier(
    model="jev-1.13.0",
    questions={
        "category": {
            "instructions": "What is this support message about?",
            "criteria": {"billing": None, "technical": None, "account": None},
        },
    },
)
result = classifier.invoke({"message": ticket_text})  # method name unconfirmed
category = result["category"]  # result shape unconfirmed
```

**After, option 2 — direct SDK call wrapped as a LangChain `Runnable`**
(safer default when the integration package's exact API can't be verified —
every shape here is the confirmed core SDK pattern from (a), just wrapped
so it composes in a LangChain chain):

```python
from langchain_core.runnables import RunnableLambda
from typesafe_sdk import Choice, TypeSafeClient

def _classify_ticket(inputs: dict) -> str:
    with TypeSafeClient(model="jev-1.13.0") as client:
        response = client.system_one(
            state={"message": inputs["message"]},
            questions={
                "category": Choice(
                    instructions="What is this support message about?",
                    criteria={"billing": None, "technical": None, "account": None},
                ),
            },
        )
    return response.choices["category"].choice

classify_ticket = RunnableLambda(_classify_ticket)
category = classify_ticket.invoke({"message": ticket_text})
```

When writing this into a user's repo, prefer option 2 unless
`TypeSafeClassifier`'s real API is confirmed first-hand (e.g. by reading its
installed source or current docs) — it only uses shapes this reference can
verify against `jev-research.md`.

---

## (c) Generic fallback — any framework with an LLM classification call

For a framework with no documented Jev integration (i.e. not Python/JS SDK,
Pydantic AI, LangChain, Cloudflare Workers AI, or LiteLLM —
`jev-research.md`, "Third-party / ecosystem integration surfaces"), fall
back to the plain REST call. The endpoint, auth, and body shape are
directly from the official API reference, so this pattern is fully
confirmed even though it isn't SDK-mediated. This is also the right pattern
when the target language has no official or community SDK at all.

**Before** — a generic `llm_classify(prompt) -> str` call site, however it's
invoked in the host framework:

```python
def llm_classify(prompt: str) -> str:
    return some_framework_llm.generate(prompt).strip()

label = llm_classify(
    f"Classify this document as spam or not_spam:\n{document_text}"
)
```

**After** — same call signature, backed by a raw HTTP call to the
documented endpoint (`jev-research.md`, "Endpoint and auth," "Request
body," "Response body"):

```python
import os
import requests

def jev_classify(state: dict, key: str, instructions: str, criteria: dict) -> dict:
    """Generic drop-in for a single-question classification call.

    Returns the raw answer object for `key` (has `choice`, `probabilities`,
    `confidence` for a `choice` question, per the documented Answer shape).
    """
    resp = requests.post(
        "https://api.typesafe.ai/v1/systemone",
        headers={
            "Authorization": f"Bearer {os.environ['TYPESAFE_API_KEY']}",
            "Content-Type": "application/json",
        },
        json={
            "state": state,
            "model": "jev-1.13.0",
            "questions": {
                key: {
                    "type": "choice",
                    "instructions": instructions,
                    "criteria": criteria,
                },
            },
        },
        timeout=10,
    )
    resp.raise_for_status()  # 401 bad key, 422 bad body, 429/529 — see below
    return resp.json()["answers"][key]

answer = jev_classify(
    state={"document": document_text},
    key="label",
    instructions="Is this document spam?",
    criteria={"spam": "Unsolicited, promotional, or malicious", "not_spam": "Legitimate content"},
)
label = answer["choice"]
```

Note the raw JSON path is `["answers"][key]["choice"]`, not
`.choices[key].choice` — that Python-SDK-specific accessor only exists when
using `typesafe_sdk`, not with a bare `requests` call (see the gotcha in
"Core call shape" above).

**Retries:** the docs recommend exponential backoff on `429`
(rate-limited) and `529` (overloaded), and note the official SDKs handle
this automatically (`jev-research.md`, "Errors and retries"). A hand-rolled
REST fallback like the one above does **not** get this for free — add
backoff around `429`/`529` explicitly, or prefer an official SDK where one
exists.

---

## Other confirmed integrations (pointers, not full patterns)

Not covered above but documented in `jev-research.md`, "Third-party /
ecosystem integration surfaces," for when the audited workflow already uses
one of these:

- **Pydantic AI** — `TypeSafeModel`, used as
  `Agent('typesafe:jev-latest', output_type=SomeModel)`; each field of
  `output_type` becomes one question, and the prompt should carry only the
  material being judged. Refuses `str` output, files, or images with a
  `UserError` — pair with `FallbackModel` for unsupported argument types.
- **Cloudflare Workers AI** — model id `typesafe/jev`, called as
  `env.AI.run('typesafe/jev', { state, questions })`.
- **LiteLLM** — pass-through provider route for TypeSafe (no further shape
  confirmed in research; verify against LiteLLM's docs before use).

For anything not in this list, use pattern (c).
