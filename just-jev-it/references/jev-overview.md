# Jev / System One — Overview

Background on TypeSafe AI's Jev model, for judging whether a decision point
in someone's workflow is Jev-shaped. Condensed from `jev-research.md`
(2026-09-22, 33 sources) — see `## Sources` below, and that artifact for
full detail and provenance.

## What It Is

**Category.** Jev is TypeSafe AI's first "System One model" (announced
2026-09-15, founded by ex-OpenAI researcher Diogo Almeida) — built to "make
fast, structured decisions that software can use directly": it evaluates a
state and returns typed answers with probabilities, rather than generating
text.

**The core mechanical distinction from an LLM:** an LLM generates text
token-by-token, sequentially, and can produce any string (including a wrong
or malformed one). Jev is transformer-based but emits **typed, structured
values** for a pre-declared set of possible answers, computed **in
parallel** in a single query, and never writes prose, code, or
explanations:

| Aspect | LLM | Jev |
|---|---|---|
| Output | Strings / generated text | Type-safe structured values |
| Sampling | Sequential (one token at a time) | Parallel (all outputs in one query) |
| Hallucination | Prone to it | "Can't hallucinate" — schema-only guarantee, see below |
| Type errors | Possible | Mathematically impossible |

Trained via "Reinforcement Learning for Calibrated Decisions (RLCD)" —
probabilities optimized against outcomes, not human preference. No weights,
parameter count, or self-hosting; hosted API only, current model
`jev-1.13.0` (aliases `jev-latest`, `jev-preview`).

**Mental model when auditing a workflow:** "the AI *decides*, software
*controls*." Jev is a specialized classifier for narrow judgment calls
inside a larger system, not a drop-in LLM replacement.

## The Three Question Primitives

Every request sends a `state` (the thing being judged) plus a map of named
`questions`. Each question is one of:

| Type | `criteria` shape | Answer | Use for |
|---|---|---|---|
| **`noul`** | optional map of `true`/`false` → outcome description | `noul`: 0–1, "probability the answer is yes" | binary judgment |
| **`choice`** | **required** map of option name → rubric, up to **255 options** | `choice` (top option), `probabilities` (map, sums to 1), `confidence` | classification, routing |
| **`score`** | **required** ordered array of **2–10** level descriptions | `score` (probability-weighted value), `legend`, `probabilities`, `confidence` | severity/quality/frustration scales |

State is **text only**: a string, JSON object, or JSON array — "images,
audio, and video are not supported." One state is evaluated against one or
more questions per request; multiple questions in a request run in parallel
and do not influence each other's answers.

## Request Shape (for reference)

```
POST https://api.typesafe.ai/v1/systemone
{ "state": ..., "model": "jev-latest", "questions": { "<key>": {type, instructions, criteria} } }
```

Response: `{ "model", "answers": {"<key>": <Answer>}, "usage" }`. Context
budget: 64k tokens/request total, 32k for state + longest question. Official
Python (`typesafe-sdk`) and JS (`@typesafe-ai/sdk`) SDKs exist, plus
integrations for Pydantic AI, Cloudflare Workers AI, Vercel AI Gateway,
LangChain, and LiteLLM. TypeSafe also ships its own "how to build with Jev"
Claude Code skill — `just-jev-it` is different: it audits an *existing*
workflow for candidate decision points, not authoring new Jev calls.

**Schema note:** some third-party writeups (e.g. DataCamp) show `options`/
`min`/`max` fields — that doesn't match the official API, which uses
`criteria` only (a map for `choice`, a 2–10-item array for `score`). Treat
`criteria` as authoritative.

## Confidence Semantics

`confidence` is **not the probability that the answer is correct.** It's a
statistic derived from how concentrated the answer's probability
distribution is — concentrated on one outcome = confident, spread out =
uncertain — so it measures the model's *certainty about its own answer*,
not accuracy. TypeSafe: "the correct threshold values depend on your domain
and the model's performance for your use case" — start conservative (0.5
floor for uncertainty, 0.9+ for high-stakes/destructive actions) and tune
against your own data. Common pattern: high confidence → act automatically;
medium → proceed cautiously/flag for review; low → route to a human.

Independent measurement (beri.net) found calibration imperfect in practice:
out-of-distribution ECE of 0.107 (4.4x the ~0.024 noise floor on public
benchmarks), yes/no answers underconfident and choice/score overconfident,
and on a question the model couldn't know, it was right only 44.7% of the
time at an average stated probability of 0.74. Treat confidence as a signal
to threshold on, not a correctness guarantee.

## Performance & Cost Claims

**Headline vendor numbers:** ~70ms–500ms end-to-end latency (vs. 3–329s for
frontier LLMs); "40x–200x faster for the same levels of frontier
intelligence"; input pricing $0.042/MTok with output "too cheap to meter"
(vs. LLM input $0.20–$10/MTok); typical cost per decision ≈$0.0004.

**Use the 193.6x faster / 444.6x cheaper figure only with its caveat.** It's
TypeSafe's own headline multiplier from a 4-workflow internal eval, which
TypeSafe itself calls "the higher end of real world gains" — measured
against a *reference answer averaging two other models* (GPT-6 Astra, Fable
5.1), not ground truth. Launch-thread commenters flagged that reference
choice and a chart showing Jev's raw accuracy below Sonnet 5's. **Never
present 193.6x/444.6x as typical or guaranteed** — prefer the narrower
"40x–200x" range or a specific independent benchmark below.

**Independent benchmarks are more mixed and task-dependent than the vendor
headline:**
- Classification (4esv/jev-eval, 300 items/task): Jev beat GPT-5.6 Terra on
  some tasks (e.g. better calibration on CLINC/polarity) and lost on others
  (Banking77 intent: 0.780 vs 0.847). Latency stayed flat (~0.17–0.20s) from
  2 to 151 answer options.
- Phishing detection (beri.net): a single Jev question underperformed Claude
  Haiku (62.6% vs 81.3%), but five decomposed questions closed the gap
  (95.0% vs 93.2%, not significant) at ~12–27x lower cost, ~3x lower latency.
- LLM-as-judge (Langfuse/Good Start Labs, 6,003 checks): $160/million graded
  answers vs. $33,000 for Claude Fable 5.1, 91.5% agreement, 20–200x faster.
- Vercel: 5–18x speedup replacing an OpenAI model for safety classification,
  with improved accuracy. Bryo AI: 10–20x lower cost than Gemini for email
  classification.

**Takeaway:** fast and cheap relative to LLM calls in every measured case;
accuracy parity is real but task-dependent, not automatic, and often needs
question decomposition to reach.

## Limitations

**Hard capability boundaries:**
- **No text generation, and answer types are fixed in advance** — every
  answer is a pre-declared `noul`/`choice`/`score`; no prose, code, or
  explanations, ever.
- **Cardinality caps** — `choice` up to 255 options, `score` 2–10 levels.
- **Text-only input, state-only context** — no images/audio/video; only
  evaluates the state passed in, nothing fetched externally; English
  primary, other languages (incl. CJK) accepted but less accurate.
- **No rationale/audit trail** — probabilities only, no explanation of
  *why*; not sufficient alone for compliance needing written justification.
- **Hosted API only** — no self-hosting, no published weights/param count.

**"Can't hallucinate" — what it actually means.** This is a *schema*
guarantee only: Jev cannot emit a value outside its declared type/options.
It says nothing about correctness — "answers can still be wrong," and it
can confidently emit "a completely wrong valid value." Calibration is not
correctness either: high confidence means predictions grouped at that
probability are right *more often on average*, not that any single answer
is right.

**Nine documented "jaggedness" weaknesses (Jev 1.13)** — accuracy degrades when the decision involves:
1. **Literal reading** — takes scoping/negation/implied conditions at face value; spell out edge cases in the criteria.
2. **Math and numbers** — recognizes answer shapes, doesn't calculate; keep arithmetic in code.
3. **Dates/times** — reads dates as text, not ordered quantities; extract with Jev, compute with code.
4. **Indirection** — multi-hop reasoning and double negatives hurt; write instructions directly, name state fields.
5. **Large irrelevant state** — unrelated detail is a distractor; send only the fields the question needs.
6. **Adversarial content** — treats state as data, not hostile; injected instructions can shift the answer.
7. **Contradictory instructions/criteria** — conflicting/overlapping categories break it; use a "two people agree" test.
8. **Structural invariants not guaranteed** — probabilities across separate questions need not sum to 1; use one `choice` question instead of deriving cross-question invariants.
9. **Generation** — not trained for it, ineffective/slow; turn extraction into a `choice` over candidate options.

Also widely reported: **Jev cannot abstain.** A forced binary/choice with no
"unknown"/"needs review" option makes it pick the least-wrong answer instead
of admitting uncertainty — add an explicit "none of these" option to every
`choice`.

**Do not use Jev for** (vendor + reviewers): prose/replies/code/summaries
(use an LLM); exact logic — math, date comparisons, counts, fixed rules
(use ordinary code); anything needing a written reasoning trace for audit;
anything requiring context beyond the submitted state. It is not a general
drop-in LLM replacement — a specialized classifier for specific decision
points inside a larger system.

**Before shipping to production**, an independent reviewer recommends:
test on ≥1,000–2,000 of your own labeled examples; calibrate per question;
add a "none of these" option to every choice; automate only above a high
confidence band (e.g. 0.99), with LLM/human fallback below it; run
adversarial/injection testing before using it as a guardrail; pin the model
version rather than tracking `jev-latest`.

## Sources

TypeSafe AI official: https://typesafe.ai/blog/introducing-system-one-models-and-jev ,
https://docs.typesafe.ai/concepts/system-one , https://docs.typesafe.ai/concepts/state ,
https://docs.typesafe.ai/confidence , https://docs.typesafe.ai/api ,
https://docs.typesafe.ai/models , https://docs.typesafe.ai/model-jaggedness/jev-1.13 ,
https://docs.typesafe.ai/llms.txt

Press / independent evaluation: https://techcrunch.com/2026/09/18/a-new-kind-of-ai-model-from-a-chatgpt-inventor-is-thrilling-developers/ ,
https://www.marktechpost.com/2026/09/19/typesafe-ai-releases-jev/ ,
https://www.tomshardware.com/tech-industry/artificial-intelligence/typesafe-ais-jev-offers-an-alternative-to-llms-that-claims-to-be-193x-faster-and-445x-cheaper-system-one-type-model-is-bespoke-for-probabilistic-decision-making ,
https://github.com/4esv/jev-eval ,
https://www.beri.net/article/typesafe-jev-typed-decision-model-calibration-decomposition-shadow-eval ,
https://langfuse.com/blog/2026-09-18-using-typesafes-jev-for-evals ,
https://news.ycombinator.com/item?id=49717558

Full research, additional integrations, and use-case citations:
`docs/superpowers/plans/artifacts/jev-research.md`.
