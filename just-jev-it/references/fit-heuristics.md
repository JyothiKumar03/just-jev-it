# Fit Heuristics

How to classify an LLM call site found during the audit phase as a Jev
candidate or not. Every entry below traces to `jev-overview.md` or the
fuller `docs/superpowers/plans/artifacts/jev-research.md` — this file adds
no new claims about Jev, only pattern-matching rules built on top of them.

**Backbone test** (community suitability checklist, cited in
`jev-research.md` under "Documented and Speculative Use Cases" — "Suitability
test published by TypeSafe-derived community reference"): a decision point
is a Jev candidate when **all** of these hold —

1. the AI *decides* rather than *creates*
2. the answer space is predefined
3. it's a single focused judgment
4. the information needed fits in the state passed to the call
5. an expert could judge it quickly from that same state
6. software consumes the result directly (branches on it, stores it as a
   typed value) rather than displaying it as prose

The signals below are ways this backbone test shows up in actual code, so
it can be applied without re-deriving it from scratch at every call site.

---

## Good Jev Fit

- **The prompt itself declares a closed output space.** Text ending in
  "answer yes/no", "pick one of: A/B/C", "respond with exactly one of these
  labels", "rate confidence 0–1", "classify as X/Y/Z/other". This is
  criterion 2 of the backbone test (predefined answer space) and maps
  directly onto Jev's three typed primitives — `noul` for yes/no, `choice`
  for a named set, `score` for an ordered scale (`jev-overview.md`, "The
  Three Question Primitives").

- **The response is re-parsed into an enum after the call.**
  `if response.strip().lower() in {"low", "medium", "high"}:`, a regex like
  `re.match(r"^(yes|no)$", ...)`, or a `json.loads`/`switch` over a fixed
  set of expected string values. A defensive fallback branch for when the
  LLM's free text *doesn't* match ("if response not in {...}: return
  default") is a strong signal — it proves the call was always meant to
  return one of a small number of typed values, and that fallback exists
  only because an LLM can't structurally guarantee it. Jev removes the
  fallback need: schema conformance is "mathematically impossible" to
  violate (`jev-research.md`, "How it differs mechanically from an LLM
  call" comparison table; "Type errors: possible" vs. "mathematically
  impossible"). Note this schema guarantee is about *shape*, not
  correctness — see the "can't hallucinate" caveat in Poor Fit / caveats
  below, and keep validating.

- **The call's output drives `if`/`elif`/`switch` control flow rather than
  being displayed or stored as content.** This is the "AI decides, software
  controls" mental model TypeSafe states directly and that this skill
  audits for (`jev-research.md`, "How it differs mechanically from an LLM
  call"; `jev-overview.md`, "Mental model when auditing a workflow").

- **The call is a named member of a documented use-case family:**
  classification, intent/ticket routing, urgency/frustration/severity
  scoring, safety or moderation classification, citation verification
  (supports/contradicts/says-nothing), spam/phishing detection, tool-call
  guardrail screening before execution, or document/search relevance
  ranking. Each has at least one named production or pilot deployment
  (`jev-research.md`, "Documented and Speculative Use Cases": Vercel safety
  classification, Bryo AI email classification, `pi-warden` tool-call
  guardrail, legal-retrieval reranking, citation verification, alert
  triage, CV screening, phishing detection).

- **All the information the call needs is already assembled in local
  variables at the call site** — no mid-call fetch of more context.
  Matches backbone criterion 4 (fits in state) and the state guidance that
  a single request evaluates one self-contained state
  (`jev-overview.md`/`jev-research.md`, "Request Shape" / "State
  guidance").

- **A confidence or probability threshold already gates the branch**, e.g.
  `if confidence > 0.8: auto_approve() else: flag_for_review()`. This is
  exactly Jev's documented "confidence-gated routing" pattern, and the
  `confidence` field is a first-class part of every `choice`/`score`
  answer (`jev-research.md`, "Officially documented architectural
  patterns" #2; "Confidence semantics").

- **An expert reading the same input could make the call in a few
  seconds** — "is this billing or technical", "does this violate policy
  X", "how severe is this, 1–5". Backbone criterion 5 directly.

- **The current prompt already asks for a fixed set of ≤255 named
  categories or a 2–10 level ordered scale.** This is a hard structural
  match to `choice` (up to 255 options) and `score` (2–10 levels)
  respectively (`jev-overview.md`, primitives table).

---

## Poor Jev Fit

- **Free text is the deliverable, consumed by a human.** Draft replies,
  summaries, generated emails, chat responses, commit messages, generated
  documentation. Directly on the vendor's "do not use Jev for" list:
  "Prose, chat replies, code, summaries — use an LLM"; Jev "do[es] not
  write replies, produce code, or generate reasoning explanations," and
  "generates no text at all" (`jev-research.md`, "Explicit 'do not use Jev
  for' list"; "Hard capability boundaries"; `jev-overview.md`, "Do not use
  Jev for").

- **The output is fed into another LLM prompt as unstructured context** —
  e.g. call A's free-text response is string-interpolated into call B's
  prompt as narrative material (not re-parsed into a typed value first).
  Because Jev can't generate text, this chain has nothing to hand to the
  next prompt (`jev-research.md`, "No text generation at all"). Distinguish
  this from a case that *looks* similar but isn't: if the only thing
  downstream code does with that free text is immediately re-parse it into
  a fixed set of values, it's actually the "re-parsed into an enum" good-fit
  signal above wearing a disguise — check what happens to the text next
  before ruling on this one.

- **The decision requires generating or selecting among options that
  aren't fixed in advance** — e.g. "suggest three possible next steps",
  "come up with a creative response", "extract the key point in your own
  words". This fails backbone criterion 1 (decides vs. creates) even
  though it superficially resembles a bounded task; per weakness #9
  ("Generation"), Jev is "not trained for it; ineffective and slow" unless
  the task can be reframed as choosing among pre-enumerated candidates
  (`jev-research.md`, "The nine documented weaknesses" #9).

- **Exact arithmetic, counting, or date/time logic embedded in the
  prompt** — "calculate days until expiration and decide if within SLA",
  "sum these totals and check the budget", "is this date before that
  one". Explicitly called out: "Jev reads dates as text, not as ordered
  quantities" and "recognizes answer shapes rather than calculating";
  vendor guidance is "keep arithmetic in code" (`jev-research.md`, "The
  nine documented weaknesses" #2 Math and numbers, #3 Date and time
  comparison; "do not use Jev for... exact logic").

- **A written rationale or explanation is part of what the call must
  return**, e.g. "explain your reasoning, then answer X" where the
  explanation text itself is stored or displayed for audit/compliance.
  Jev "returns probabilities only, with no natural-language explanation of
  *why*" and explicitly cannot satisfy "anything needing a written
  reasoning trace for audit" (`jev-research.md`, "No rationale / audit
  trail"; "do not use Jev for" list).

- **The call needs to fetch more information mid-decision** — a
  retrieval/tool-use loop where the model decides what to search for next,
  or any step that pulls in context beyond what's already in scope at the
  call site. "Jev only evaluates the state you pass in" — it cannot fetch
  outside context itself (`jev-research.md`, "No external context";
  "Anything requiring retrieval of context outside the submitted state").

- **The call operates on images, audio, video, or on non-English/CJK
  content where accuracy matters.** State is text-only ("images, audio,
  and video are not supported"); non-English languages including CJK are
  accepted but "currently have lower accuracy" (`jev-research.md`,
  "Text-only input"; "Language").

- **Multi-turn dialogue where the "decision" is really "what should be
  said next" in an open-ended conversation**, as opposed to a single
  snapshot judgment about a conversation's content. Passing a chat
  transcript *as state* for a bounded judgment (e.g. "does the latest user
  message show disagreement?") is a documented, good-fit pattern — see the
  Langfuse `noul` example in `jev-research.md`. What's a poor fit is asking
  the model to manage or continue the dialogue itself; Jev has no
  conversational memory of its own and each request evaluates one state
  against fixed questions in a single, independent call
  (`jev-research.md`, "State guidance" — "one state... one or more
  questions"; "Officially documented architectural patterns").

**Caveat that applies even to good-fit matches:** the schema guarantee
("can't hallucinate") only means the answer will be a validly-typed
`noul`/`choice`/`score` — "answers can still be wrong." A migrated call
still needs validation against labeled data before it's trusted in
production (`jev-research.md`, "'Can't hallucinate' — what it actually
means"; "Pre-production checklist recommended by the independent
reviewer").

---

## Worked Examples

The following are **illustrative sketches only** — they show the shape of
a before/after migration using the `noul`/`choice`/`score` primitives from
`jev-overview.md`, using the same Python SDK call shape documented in
`jev-research.md` ("API / Integration Shape" — Python example). They have
**not** been run against a live Jev API and should not be treated as
verified-working code; `references/integration-patterns.md` and
`scripts/validate_with_jev.py` are where an actual migration gets checked.

### Example 1 — Ticket priority classification (Good Fit)

Before: prompt already declares a 3-way closed output space, and the code
defensively re-parses free text into that same set — both good-fit signals
above.

```python
def classify_priority(ticket_text, llm):
    prompt = (
        f"Classify this ticket's priority as low, medium, or high:\n"
        f"{ticket_text}\nAnswer with one word."
    )
    response = llm.complete(prompt)
    if response.strip().lower() not in {"low", "medium", "high"}:
        return "medium"  # fallback for a malformed LLM answer
    return response.strip().lower()
```

After (sketch — illustrative, not verified):

```python
# ILLUSTRATIVE SKETCH — shape only, not verified against a live Jev API call.
from typesafe_sdk import Choice, TypeSafeClient

def classify_priority(ticket_text, jev_client):
    response = jev_client.system_one(
        state={"ticket": ticket_text},
        questions={
            "priority": Choice(
                instructions="What priority should this support ticket be assigned?",
                criteria={
                    "low": "Minor issue, no urgency",
                    "medium": "Normal issue, standard turnaround",
                    "high": "Urgent, blocking, or high-impact issue",
                },
            ),
        },
    )
    return response.choices["priority"].choice
```

The manual fallback branch disappears because the schema guarantees a
valid value — but per the caveat above, that's a guarantee about *shape*,
not correctness; validate against real tickets before trusting it.

### Example 2 — Drafting a customer reply (Poor Fit, no migration)

```python
def draft_reply(ticket_text, llm):
    """Draft a free-text reply to the customer. Not a classification task."""
    prompt = f"Write a helpful, empathetic reply to this support ticket:\n{ticket_text}"
    return llm.complete(prompt)
```

Verdict: poor fit, leave on the LLM path. The output is prose consumed
directly by a human — squarely on the "do not use Jev for" list (prose,
chat replies). No typed-schema replacement applies here; there is no
"after" sketch because forcing this into `noul`/`choice`/`score` would
mean asking Jev to generate the reply text, which it structurally cannot
do.

### Example 3 — Tool-call guardrail with confidence gating (Good Fit)

Before: free-text answer parsed for a yes/no plus an ad hoc confidence
number.

```python
def should_allow_tool_call(tool_name, args, context, llm):
    prompt = (
        f"A coding agent wants to run: {tool_name}({args})\n"
        f"Context: {context}\n"
        "Is this action safe and within scope? Answer yes or no, "
        "and state your confidence from 0 to 1."
    )
    response = llm.complete(prompt)
    # ... regex parsing of "yes/no" + a confidence number out of free text ...
```

After (sketch — illustrative, not verified), modeled on the documented
`pi-warden`-style guardrail pattern and the vendor's confidence-gated
routing pattern. Note this uses `choice`, not `noul`: only `choice` and
`score` answers carry a `confidence` field per the documented API
(`jev-overview.md`/`jev-research.md` primitives table — `noul` returns only
the `noul` probability), and an explicit `needs_review` option is added to
the schema itself rather than derived in code, per the beri.net
recommendation below:

```python
# ILLUSTRATIVE SKETCH — shape only, not verified against a live Jev API call.
from typesafe_sdk import Choice, TypeSafeClient

def should_allow_tool_call(tool_name, args, context, jev_client):
    result = jev_client.system_one(
        state={"tool_call": f"{tool_name}({args})", "context": context},
        questions={
            "verdict": Choice(
                instructions="Is this tool call safe, in scope, and reversible?",
                criteria={
                    "allow": "Action is safe, in scope, and low-risk",
                    "block": "Action is risky, out of scope, or irreversible",
                    "needs_review": "Not clearly safe or unsafe from the given context",
                },
            ),
        },
    )
    verdict = result.choices["verdict"].choice
    confidence = result.choices["verdict"].confidence
    if verdict in {"allow", "block"} and confidence > 0.9:
        return verdict
    return "needs_review"  # low confidence, or the model already said so itself
```

The explicit `needs_review` option is not optional flourish: Jev "cannot
abstain" on a forced binary/choice with no such option, so it has to be
added to the schema itself, not left to the model to invent
(`jev-research.md`, "cannot abstain" note; beri.net pre-production
recommendation to "add an explicit 'none of these' option to every
choice"). The confidence check on top is still needed — a low-confidence
`allow` or `block` should route to review too.
