# Jev / TypeSafe AI — Research Artifact

**Research date:** 2026-09-22
**Purpose:** Factual foundation for the `just-jev-it` skill's reference docs (`jev-overview.md`, `fit-heuristics.md`, `integration-patterns.md`) and validation script.
**Rule applied:** every specific number, API detail, and use case below carries an adjacent source URL, or sits explicitly under a "speculative / plausible extrapolation" heading. Nothing here is invented.

---

## What Jev Is

**Category.** Jev is the first "System One model" from TypeSafe AI, announced 2026-09-15 and covered in press from 2026-09-18. TypeSafe defines System One models as "a new class of frontier models built to make fast, structured decisions that software can use directly" — they "evaluate a state and return typed answers with probabilities" rather than generating text. ([typesafe.ai blog](https://typesafe.ai/blog/introducing-system-one-models-and-jev), [docs.typesafe.ai/concepts/system-one](https://docs.typesafe.ai/concepts/system-one))

**Founder / company.** Founded by Diogo Almeida, a former OpenAI researcher who worked on the instruction-following research behind ChatGPT and on RLHF; he left roughly two years before launch to start TypeSafe AI. About half the team works on synthetic-data methodology, and Almeida states the model is trained exclusively on synthetic data. ([TechCrunch](https://techcrunch.com/2026/09/18/a-new-kind-of-ai-model-from-a-chatgpt-inventor-is-thrilling-developers/))

**Naming.** "System One" references Kahneman's fast/System 1 thinking in *Thinking, Fast and Slow*; "Jev" references William Stanley Jevons (the Jevons paradox — cheaper intelligence unlocking more use cases). ([typesafe.ai blog](https://typesafe.ai/blog/introducing-system-one-models-and-jev))

**Architecture.** It is a transformer-based model but *not* a large language model: it emits probabilities — what TypeSafe calls "calibrated decisions" — instead of tokens of text. ([TechCrunch](https://techcrunch.com/2026/09/18/a-new-kind-of-ai-model-from-a-chatgpt-inventor-is-thrilling-developers/)) No weights, parameter count, or self-hosting option have been published; access is a hosted API. ([MarkTechPost](https://www.marktechpost.com/2026/09/19/typesafe-ai-releases-jev/))

**How it differs mechanically from an LLM call** — TypeSafe's own comparison table ([typesafe.ai blog](https://typesafe.ai/blog/introducing-system-one-models-and-jev)):

| Aspect | LLM | Jev / System One |
| --- | --- | --- |
| Training objective | RLHF / RLVR | "Reinforcement Learning for Calibrated Decisions (RLCD)" |
| Output format | "Strings / generated text" | "Type-safe structured values" |
| Sampling | "Sequential. Generates one token at a time" | "Parallel. Generates all outputs in a single query" |
| Hallucination | Prone to hallucinating | "can't hallucinate" (see Limitations — this means *schema* conformance only) |
| Type errors | Possible | "mathematically impossible" |

Further mechanical points from the docs:

- Questions in a single request are evaluated **in parallel against a shared state**, and answers do not influence one another. ([docs.typesafe.ai/llms.txt](https://docs.typesafe.ai/llms.txt), [community reference gist](https://gist.github.com/pjburnhill/adf8d28efcad9df037bfdece178ef965))
- The model "do[es] not write replies, produce code, or generate reasoning explanations." ([docs.typesafe.ai/concepts/system-one](https://docs.typesafe.ai/concepts/system-one))
- Probabilities are "optimized against outcomes to reflect uncertainty" rather than against human preference. ([docs.typesafe.ai/concepts/system-one](https://docs.typesafe.ai/concepts/system-one))
- The mental model TypeSafe pushes: the AI *decides*, software *controls* — "Keep code in control: use software for deterministic logic; reserve AI for judgment calls." ([docs.typesafe.ai/llms.txt](https://docs.typesafe.ai/llms.txt))

---

## API / Integration Shape

TypeSafe's API is publicly documented at `docs.typesafe.ai`. Details below are from the official API reference unless otherwise noted.

### Endpoint and auth

```
POST https://api.typesafe.ai/v1/systemone
Authorization: Bearer <API_KEY>
Content-Type: application/json
```

([docs.typesafe.ai/api](https://docs.typesafe.ai/api))

SDKs read the key from the `TYPESAFE_API_KEY` environment variable. ([typesafe-sdk-python README](https://github.com/typesafe-ai/typesafe-sdk-python), [typesafe-sdk-js README](https://github.com/typesafe-ai/typesafe-sdk-js))

### Request body

Three required fields ([docs.typesafe.ai/api](https://docs.typesafe.ai/api)):

- **`state`** — `string | object | array`. "Content to evaluate — plain text, chat logs, or structured application data."
- **`model`** — `string`. `"jev-latest"` is the flagship alias.
- **`questions`** — `map<string, Question>`. Caller chooses the keys; answers come back under the same keys.

**State guidance** ([docs.typesafe.ai/concepts/state](https://docs.typesafe.ai/concepts/state)): a string for a single piece of text; a JSON object for "named fields, related records, or application state"; a JSON array for "a sequence of messages or records." Each request evaluates **one** state against one or more questions. "Put related information together when the decision requires comparing those parts." State is **text only** — "Images, audio, and video are not supported." English is primary; "other languages, including CJK scripts, are accepted but currently have lower accuracy."

### The three question primitives

All questions share `type` and `instructions`; each adds its own `criteria` ([docs.typesafe.ai/api](https://docs.typesafe.ai/api)):

| Type | `criteria` | Answer fields |
| --- | --- | --- |
| **`noul`** (yes/no) | optional object mapping `true` / `false` to outcome descriptions | `noul` (number, 0 = no, 1 = yes) — "the probability that the answer is yes" |
| **`choice`** | **required** map of option name → rubric description; **up to 255 options**, null values allowed | `choice` (highest-probability option), `probabilities` (map, sums to 1), `confidence` (0–1) |
| **`score`** | **required** array of **2–10** ordered level descriptions | `score` (probability-weighted value), `legend` (level index → description), `probabilities` (sums to 1), `confidence` (0–1) |

([docs.typesafe.ai/api](https://docs.typesafe.ai/api), [docs.typesafe.ai/llms-full.txt](https://docs.typesafe.ai/llms-full.txt))

### Response body

```
{
  "model":   "<string>",
  "answers": { "<question key>": <Answer>, ... },
  "usage":   { "input_tokens": <int>, "output_tokens": <int> }
}
```

([docs.typesafe.ai/api](https://docs.typesafe.ai/api))

### Confidence semantics

`confidence` is **not** the probability that the answer is right — it is "a statistic computed from the probability distribution the answer already gives you": "concentrated on one outcome means a confident answer, spread out means an uncertain one." For three options the docs give the approximation `(3 × largest probability − 1) / 2`. ([docs.typesafe.ai/confidence](https://docs.typesafe.ai/confidence))

The docs recommend a three-tier pattern — **high** confidence: act automatically; **medium**: proceed cautiously / confirm / flag for review; **low**: do not act, route to a human or another system — with a 0.5 floor for genuine uncertainty and 0.9+ for high-stakes destructive actions. Crucially: "The correct threshold values depend on your domain and the model's performance for your use case. Start with conservative thresholds, test with your own data, and adjust as you observe results." ([docs.typesafe.ai/confidence](https://docs.typesafe.ai/confidence))

### Errors and retries

| Status | Meaning |
| --- | --- |
| 401 | Invalid / missing API key |
| 422 | Invalid request body |
| 429 | Rate limit exceeded |
| 529 | Service overloaded |

Exponential backoff recommended for 429/529; the official SDKs handle this automatically. ([docs.typesafe.ai/api](https://docs.typesafe.ai/api))

### Models, context, and rate limits

- Current model: **Jev 1.13**, id `jev-1.13.0`. Aliases `jev-latest` and `jev-preview` both point at it. ([docs.typesafe.ai/models](https://docs.typesafe.ai/models))
- Context: **64k tokens per request total** (state + all questions), with a separate cap of **32k tokens for state + longest question**. ([docs.typesafe.ai/models](https://docs.typesafe.ai/models)) Note: Cloudflare's Workers AI listing states a 32,000-token context window for its hosted variant. ([Cloudflare AI docs](https://developers.cloudflare.com/ai/models/typesafe/jev/))
- Rate limits: **250,000 tokens/second** and **1,200 requests/minute**, returning 429 when exceeded; docs warn "Rate limits are adjusting dynamically" due to demand, with higher enterprise limits available. ([docs.typesafe.ai/models](https://docs.typesafe.ai/models))

### Official SDKs and repos (github.com/typesafe-ai)

| Repo | Description | Stars (as of research date) |
| --- | --- | --- |
| `typesafe-sdk-python` | "The official Python library for the TypeSafe API" (MIT) | ~200 |
| `typesafe-sdk-js` | "The official TypeScript/JavaScript library for the TypeSafe API" (MIT) | ~225 |
| `system-one-adapter-python` | "Drop-in TypeSafeClient replacement backed by LLM APIs" (MIT) | ~257 |
| `skills` | "Agent skills for building with TypeSafe's System One API" (MIT) | ~1,771 |

([github.com/typesafe-ai](https://github.com/typesafe-ai))

Python (3.10+) package `typesafe-sdk`; JavaScript package `@typesafe-ai/sdk`; cURL also supported. ([MarkTechPost](https://www.marktechpost.com/2026/09/19/typesafe-ai-releases-jev/))

**Python example** ([typesafe-sdk-python README](https://github.com/typesafe-ai/typesafe-sdk-python)):

```python
from typesafe_sdk import Choice, TypeSafeClient

with TypeSafeClient() as client:
    response = client.system_one(
        state={"document": "I was charged twice. Please fix this ASAP."},
        questions={
            "category": Choice(
                instructions="What is this ticket about?",
                criteria={"billing": None, "technical": None, "other": None},
            ),
        },
    )

print(response.choices["category"].choice)
```

Install shown as `uv add typesafe-sdk`.

**TypeScript example** ([typesafe-sdk-js README](https://github.com/typesafe-ai/typesafe-sdk-js)):

```typescript
import { choice, TypeSafeClient } from "@typesafe-ai/sdk";

const client = new TypeSafeClient();
const response = await client.systemOne({
  state: { document: "I was charged twice. Please fix this ASAP." },
  questions: {
    category: choice("What is this ticket about?", {
      billing: null,
      technical: null,
      other: null,
    }),
  },
});
// response.answers.category.choice
```

Install: `npm install @typesafe-ai/sdk`. The package infers answer types from the questions defined, and ships ESM, CJS, and TypeScript declarations.

**Noul example** with model pinning, from a third-party integration guide ([Langfuse](https://langfuse.com/blog/2026-09-18-using-typesafes-jev-for-evals)):

```python
from typesafe_sdk import Noul, NoulCriteria, TypeSafeClient

USER_DISAGREEMENT = Noul(
    instructions="Does the user message show disagreement with prior response?",
    criteria=NoulCriteria(
        true="User clearly rejects or challenges the assistant",
        false="User does not clearly reject prior response",
    ),
)

with TypeSafeClient(model="jev-1.13.0") as jev:
    result = jev.system_one(state={...}, questions={"user_disagreement": USER_DISAGREEMENT})
    p_disagreement = result.nouls["user_disagreement"].noul
```

> **Schema discrepancy to be aware of when writing the skill.** DataCamp's guide shows a request using `{"type": "choice", "options": [...]}` and `{"type": "score", "min": 0, "max": 100}` ([DataCamp](https://www.datacamp.com/blog/system-one-models-jev)). This does **not** match the official API reference, which uses `criteria` (a map for `choice`, an ordered array of 2–10 level descriptions for `score`) and has no `options`/`min`/`max` fields ([docs.typesafe.ai/api](https://docs.typesafe.ai/api)). Treat the official reference as authoritative; the validation script should flag `options`/`min`/`max` as an incorrect shape.

### Third-party / ecosystem integration surfaces

- **Official agent skill.** TypeSafe ships its own Claude Code plugin — `claude plugin marketplace add typesafe-ai/skills` then `claude plugin install typesafe@typesafe-ai`; for other agents, `npx skills add typesafe-ai/skills --skill typesafe-ai`. In Claude Code it is invoked as `/typesafe:typesafe-ai`, and its described purpose is to "Design TypeSafe workflows, find current docs and cookbooks, and compose typed judgments in code." ([github.com/typesafe-ai/skills](https://github.com/typesafe-ai/skills), [docs.typesafe.ai/llms-full.txt](https://docs.typesafe.ai/llms-full.txt)) **This matters for positioning `just-jev-it`: an official "how to build with Jev" skill already exists; our differentiator is auditing an *existing* workflow for replaceable decision points, not greenfield authoring.**
- **Pydantic AI** — `TypeSafeModel`, used as `Agent('typesafe:jev-latest', output_type=SomeModel)`. Each output-model field becomes one question; the prompt carries *only* the material being judged, since "a question written into the prompt is text to be judged, and Jev judges it." Refuses `str` output, files, or images with a `UserError` before sending. Pairs with `FallbackModel` for unsupported argument types. ([Pydantic docs](https://pydantic.dev/docs/ai/models/typesafe/))
- **Cloudflare Workers AI** — model id `typesafe/jev`, called as `env.AI.run('typesafe/jev', { state, questions })`. ([Cloudflare AI docs](https://developers.cloudflare.com/ai/models/typesafe/jev/))
- **Vercel AI Gateway** — Jev exposed via AI SDK 7's `evaluate` method, no waitlist as of 2026-09-16. ([Firecrawl blog](https://www.firecrawl.dev/blog/what-is-jev))
- **LangChain** — `TypeSafeClassifier`, accepting "text, structured data, or LangChain messages" as state. ([LangChain blog](https://www.langchain.com/blog/building-a-harness-with-jev))
- **LiteLLM** — pass-through provider route for TypeSafe. ([LiteLLM docs](https://docs.litellm.ai/docs/pass_through/typesafe))
- **OpenRouter** — community SDK guide for the TypeSafe SDK. ([OpenRouter](https://openrouter.ai/docs/guides/community/typesafe-sdk))
- **Community SDKs** catalogued in awesome-jev: Swift, Go (`jev-go`), Elixir (`jev`), PHP/Laravel (`laravel-typesafe-jev`), Python (`jevclient`), plus multiple MCP servers (`jev-mcp`, `Jevbridge`, `decide-mcp`). ([awesome-jev](https://github.com/yibie/awesome-jev))
- **Playground / console** — `https://console.typesafe.ai/playground`. ([typesafe.ai blog](https://typesafe.ai/blog/introducing-system-one-models-and-jev))

### Officially documented architectural patterns

From [docs.typesafe.ai/patterns](https://docs.typesafe.ai/patterns) and [docs.typesafe.ai/llms-full.txt](https://docs.typesafe.ai/llms-full.txt):

1. **Speculative fan-out** — "Send many questions in a single call, including speculative ones, and let your code decide what's relevant." Response time barely increases when adding questions to a single request ([LangChain blog](https://www.langchain.com/blog/building-a-harness-with-jev)).
2. **Confidence-gated routing** — "Utilize confidence as a second decision axis to build safer systems"; different thresholds for different actions based on consequences.
3. **Composite scoring** — combine "several dimensions of analysis into a single score" via weighted sums computed in code.
4. **Intent routing** — classify user intent and "route to the appropriate handler."

Design principles stated alongside them: "Ask narrow questions" (decompose complex decisions into atomic judgments); "Structure your state" (nested JSON, relevant context only); "Route on uncertainty." ([docs.typesafe.ai/llms.txt](https://docs.typesafe.ai/llms.txt))

---

## Documented and Speculative Use Cases

### Confirmed in a published source

Each entry below is reported by a named source. Where a source reports measured numbers, they are included with the same citation.

**Vendor-stated categories** ([typesafe.ai blog](https://typesafe.ai/blog/introducing-system-one-models-and-jev), [docs.typesafe.ai/concepts/system-one](https://docs.typesafe.ai/concepts/system-one)):
- "AI-Powered Workflows / smart if-statements"
- "Map-reducing over big data"
- "Real-time applications" (citing ~100ms speeds)
- "Verify everything" — scoring, judging, and guardrailing LLM outputs
- Classification, routing, scoring, extraction, and branching tasks
- Intent routing example in docs: classify a support ticket into `billing` / `technical` / `account`, score frustration 0–2, and gate on confidence for human review

**Named production / pilot deployments:**

- **Vercel — safety classification.** Replaced an OpenAI model for safety classification and reported results "5 to 18 times faster" with improved accuracy. ([TechCrunch](https://techcrunch.com/2026/09/18/a-new-kind-of-ai-model-from-a-chatgpt-inventor-is-thrilling-developers/))
- **Vercel — `eve` agent framework.** Uses Jev as its default evaluator. ([awesome-jev](https://github.com/yibie/awesome-jev))
- **Bryo AI — business email classification.** Jev cost 10–20× less than Gemini in their test, with the cited unique advantage of returning genuine probability scores usable for workflow automation. ([TechCrunch](https://techcrunch.com/2026/09/18/a-new-kind-of-ai-model-from-a-chatgpt-inventor-is-thrilling-developers/))
- **Coding-agent guardrail (`pi-warden`)** — screens bash/write/edit tool calls before execution on irreversibility, task alignment, and scope. Over 17,000 recorded calls it held 42 times, and "roughly 88% of those holds were right," at ~250ms per judgment. ([Firecrawl blog](https://www.firecrawl.dev/blog/what-is-jev))
- **Search-result reranking (legal retrieval)** — BM25 shortlist scored with one Noul per query-candidate pair; top-1 accuracy improved "from 5% to 18% and top-10 from 38% to 62%," with 1,200 scoring calls costing "$0.0645." ([Firecrawl blog](https://www.firecrawl.dev/blog/what-is-jev))
- **Citation verification** — string matching plus a Choice question over `supports` / `contradicts` / `says_nothing`; "four accurate citations came back verified at confidence 0.93 or higher, and all four planted failures were caught." ([Firecrawl blog](https://www.firecrawl.dev/blog/what-is-jev))
- **Documentation classification** — Every's independent test ran "777 judgments in 0.7 seconds" for approximately "$0.00025" total. ([Firecrawl blog](https://www.firecrawl.dev/blog/what-is-jev))
- **Writing-quality assessment** — median 0.35s per passage vs 8.83s for a frontier model; "Jev caught six of seven planted defects," at slightly lower accuracy than Fable 5.1. ([Firecrawl blog](https://www.firecrawl.dev/blog/what-is-jev))
- **Model routing by difficulty** — Vercel's AI Gateway evaluates a prompt against repository context to route to the appropriate model tier. ([Firecrawl blog](https://www.firecrawl.dev/blog/what-is-jev)); LangChain describes the same pattern: "route requests to different models based on complexity." ([LangChain blog](https://www.langchain.com/blog/building-a-harness-with-jev))
- **Agent safety guardrails / auto-mode** — classification of dangerous tool calls before execution; LangChain notes this pattern "has been locked away in closed source parts" of coding harnesses. ([LangChain blog](https://www.langchain.com/blog/building-a-harness-with-jev))
- **Browser automation agents** — Kyle Jeong powers browser automation agents "for fractions of a cent." ([LangChain blog](https://www.langchain.com/blog/building-a-harness-with-jev))
- **Live trading agent** — built by Jarrod Watts. ([LangChain blog](https://www.langchain.com/blog/building-a-harness-with-jev))
- **Email triage at scale** — Ryan Vogel. ([LangChain blog](https://www.langchain.com/blog/building-a-harness-with-jev))
- **LLM-as-judge replacement for evals (Langfuse)** — scoring traces with a Noul for user disagreement. Good Start Labs benchmark over 6,003 rubric checks: "$160 per million graded answers" vs Claude Fable 5.1's "$33,000," "91.5% agreement" with Fable 5.1, and "20 to 200x faster" than frontier models. ([Langfuse](https://langfuse.com/blog/2026-09-18-using-typesafes-jev-for-evals))
- **Alert triage (`jev-oncall`)** — 418ms p50, $0.04 per 1,000 alerts. ([awesome-jev](https://github.com/yibie/awesome-jev))
- **Document relevance at scale (`DocJev`, LlamaIndex)** — 40-document pilot, 182ms p50 latency. ([awesome-jev](https://github.com/yibie/awesome-jev))
- **Marketing routing (`Notra`)** — GEO marketing platform with 0.5s threshold routing. ([awesome-jev](https://github.com/yibie/awesome-jev))
- **CV / recruiting screening (`typesafe-jev CV screener`)** — with editable policy. ([awesome-jev](https://github.com/yibie/awesome-jev))
- **Phishing / spam detection** — benchmarked by an independent reviewer at 95.0% accuracy when decomposed into five narrow questions. ([beri.net](https://www.beri.net/article/typesafe-jev-typed-decision-model-calibration-decomposition-shadow-eval))

**Practitioner-reported in the Hacker News launch thread** ([HN 49717558](https://news.ycombinator.com/item?id=49717558)):
- Support ticket triage — classifying tone, urgency, and issue type with calibrated confidence
- Home automation — parsing natural-language commands into structured device actions (demonstrated via Home Assistant)
- Entity resolution — matching genealogical records, where an LLM-based approach was computationally infeasible
- Design-by-contract integration — structured output plus semantic branching for agentic workflows
- Spam/phishing detection — high-volume classification

**Use-case categories catalogued by awesome-jev** with entry counts ([awesome-jev](https://github.com/yibie/awesome-jev)): Classification & Routing (33), Verification & Guardrails (28), Agent Decisions (40), Infra/SDKs/Integrations (57), Evaluation & Benchmarking (24), Scoring & Ranking (24), Calibration & Research (23), Game & Simulation (18), Adaptive & Realtime UI (8), Data Labeling & Curation (6), Content Moderation (7), Finance & Trading (4), Compliance & Legal (1). *Caveat from the list's own maintainers: "Listings are not endorsements"; "Treat same-day bulk submissions with particular care"; several projects are unproven prototypes.*

**Suitability test published by TypeSafe-derived community reference** ([gist](https://gist.github.com/pjburnhill/adf8d28efcad9df037bfdece178ef965)) — a decision point is a Jev candidate when: the AI *decides* rather than creates; the answer space is predefined; it's a single focused judgment; the required information fits in state; an expert could judge it quickly; and software consumes the result directly. Use-case families listed there: classification (intent, department, document type), detection (fraud, sensitivity, safeguarding), scoring (severity, relevance, quality), routing (workflow selection, specialist assignment), search/retrieval ranking, and verification (policy compliance, requirement satisfaction).

### Plausible extrapolation (NOT confirmed by any source found)

These fit the documented primitives and the published suitability test, but **no source was found reporting an actual deployment**. They must be labeled as untested suggestions in the shipped skill, never presented as proven.

- **Feature flagging** — deciding flag exposure per request from user/session state. Shape-compatible with `choice`/`noul`, but no published example found.
- **A/B decisioning / variant selection** — selecting an experiment arm based on semantic state. No published example found; note that random assignment is a deterministic-code job and only the *semantic eligibility* part would be Jev-shaped.
- **Retry / escalation logic** — deciding whether a failure is transient (retry) vs terminal (escalate) from an error payload. Conceptually adjacent to the documented alert-triage and confidence-gated-routing patterns, but not separately reported.
- **Fraud / risk scoring** — the community reference lists "detection (fraud...)" as a category ([gist](https://gist.github.com/pjburnhill/adf8d28efcad9df037bfdece178ef965)) and awesome-jev has a Finance & Trading category with 4 entries ([awesome-jev](https://github.com/yibie/awesome-jev)), but no specific named fraud-scoring deployment with numbers was found. Also note the documented arithmetic/date weaknesses make pure numeric risk scoring a poor fit.
- **Approval workflows** — e.g. expense or PR approval gating. The CV-screener and guardrail patterns are the closest documented analogues; a general approval-workflow deployment was not found.
- **Content moderation gates** — awesome-jev lists a Content Moderation category (7 entries) and Vercel's use is "safety classification" ([awesome-jev](https://github.com/yibie/awesome-jev), [TechCrunch](https://techcrunch.com/2026/09/18/a-new-kind-of-ai-model-from-a-chatgpt-inventor-is-thrilling-developers/)), so the *category* is confirmed; specific moderation-policy deployments with measured outcomes were not found.
- **Agent tool-selection** — awesome-jev's Agent Decisions category explicitly mentions "tool selection" ([awesome-jev](https://github.com/yibie/awesome-jev)); confirmed as a category, but the only measured example found is guardrail-style *screening* of tool calls (`pi-warden`), not selection among tools.

---

## Performance & Cost Claims

### Vendor-published claims (TypeSafe's own numbers)

| Claim | Value | Source |
| --- | --- | --- |
| End-to-end latency | "70ms-500ms" vs "3 to 329 seconds" for frontier LLMs | [typesafe.ai blog](https://typesafe.ai/blog/introducing-system-one-models-and-jev) |
| General speedup | "40x-200x faster for the same levels of frontier intelligence" | [typesafe.ai blog](https://typesafe.ai/blog/introducing-system-one-models-and-jev) |
| Headline multipliers | "193.6x faster, 444.6x cheaper" — TypeSafe notes this is the "higher end of real world gains" | [typesafe.ai blog](https://typesafe.ai/blog/introducing-system-one-models-and-jev); reported as "193x faster and 445x cheaper" by [Tom's Hardware](https://www.tomshardware.com/tech-industry/artificial-intelligence/typesafe-ais-jev-offers-an-alternative-to-llms-that-claims-to-be-193x-faster-and-445x-cheaper-system-one-type-model-is-bespoke-for-probabilistic-decision-making) |
| Input price | $0.042 / MTok ($42 per billion tokens) | [docs.typesafe.ai/models](https://docs.typesafe.ai/models), [typesafe.ai blog](https://typesafe.ai/blog/introducing-system-one-models-and-jev) |
| Output price | Free — "too cheap to meter" | [typesafe.ai blog](https://typesafe.ai/blog/introducing-system-one-models-and-jev), [docs.typesafe.ai/models](https://docs.typesafe.ai/models) |
| LLM baseline for comparison | LLM input "$0.20 to $10 / MTok," output "~5x more expensive than input" | [typesafe.ai blog](https://typesafe.ai/blog/introducing-system-one-models-and-jev) |
| Typical per-decision cost | ≈$0.0004 per decision | [docs.typesafe.ai](https://docs.typesafe.ai/) (as surfaced in search of the docs site) |
| Typical latency | ~100ms per request; questions run in parallel | [docs.typesafe.ai/llms-full.txt](https://docs.typesafe.ai/llms-full.txt) |
| Intelligence parity | "similar levels of intelligence on System One tasks compared to existing LLMs" | [typesafe.ai blog](https://typesafe.ai/blog/introducing-system-one-models-and-jev) |

**Critical methodology caveat on the headline multipliers.** The 193.6x/444.6x figures come from TypeSafe's own 4-workflow evaluation, where "the reference answer is the average of GPT-6 Astra and Fable 5.1" — i.e. compared against an average of two models rather than ground truth — and TypeSafe "expects these gains to sit at the high end of real use." ([MarkTechPost](https://www.marktechpost.com/2026/09/19/typesafe-ai-releases-jev/)) Hacker News commenters flagged the two-model-average reference as an unusual choice, and noted a shared chart showing Jev's raw accuracy below Sonnet 5's; TypeSafe also said it would skip public benchmark leaderboards and publish only one-off evals tied to product updates. ([HN discussion, via search of](https://news.ycombinator.com/item?id=49717558))

### Vendor 4-workflow benchmark, accuracy vs cost vs latency

On TypeSafe's own 4-workflow benchmark: Jev **67.8%** accuracy, roughly tied with GPT-5.6 Terra (**67.9%**), a few points below GPT-5.6 Sol (**74.1%**) and Opus 5 (**73.1%**); Jev **~$0.0004/case** vs **$0.0304–$0.1761** for those LLMs; **0.4s** vs **10–38s**. ([OpenTweet benchmark writeup](https://opentweet.io/jev/vs-gpt))

### Independent benchmarks found

**1. `4esv/jev-eval` — independent classification eval** ([github.com/4esv/jev-eval](https://github.com/4esv/jev-eval))

Methodology: Jev 1.13.0 vs GPT-5.6 Terra (via OpenRouter) and local open-weight clones (Laya 421M, open-jev 435M, Kev-0.8B) on classification tasks, 300 items each, local models on an M-series GPU. "API models include the network; local models are the forward pass with the model resident, measured after warm-up."

Accuracy (300 items/task):

| Task | Options | Jev | Terra | open-jev | Kev-0.8B | Laya |
| --- | --- | --- | --- | --- | --- | --- |
| CLINC (out-of-sample) | 151 | **0.897** | — | 0.610 | 0.643 | 0.497 |
| Intent (Banking77) | 77 | 0.780 | 0.847 | **0.873** | 0.770 | 0.370 |
| Sentiment5 (SST-5) | 5 | 0.570 | **0.593** | 0.560 | 0.510 | 0.310 |
| Polarity (IMDB) | 2 | **0.970** | **0.970** | 0.957 | 0.953 | 0.507 |

ECE / p50 latency:

| Task | Jev | Terra | open-jev | Kev-0.8B | Laya |
| --- | --- | --- | --- | --- | --- |
| CLINC | **0.039** / 0.17s | — | 0.072 / 0.43s | 0.260 / 0.87s | 0.471 / **0.16s** |
| Intent | 0.110 / 0.20s | 0.081 / 1.04s | **0.047** / 0.27s | 0.146 / 0.67s | 0.520 / **0.10s** |
| Sentiment5 | 0.200 / 0.19s | 0.303 / 1.06s | **0.052** / 0.07s | 0.110 / 0.13s | 0.317 / **0.04s** |
| Polarity | 0.042 / 0.20s | **0.020** / 1.04s | 0.036 / 0.17s | 0.030 / 0.37s | 0.496 / **0.08s** |

Key findings: Jev's latency is essentially flat in option count — "From 2 to 151 options its p50 moves 0.17 to 0.20 s" — while local clones degrade; clones that list a dataset as training data beat Jev on it (open-jev 0.873 vs Jev 0.780 on Banking77) but trail badly on the unseen CLINC (−28.7 points); Jev is insensitive to question phrasing where Laya is not. Caveats stated by the author: one run on one machine, no prompt tuning, differences under ~5 points are noise at n=300, datasets are public and old, Terra's confidence is self-reported, and local vs API latencies measure different quantities.

**2. beri.net — calibration and decomposition study** ([beri.net](https://www.beri.net/article/typesafe-jev-typed-decision-model-calibration-decomposition-shadow-eval))

- Phishing detection, single question: Jev **62.6%** vs Claude Haiku **81.3%**. Decomposed into five narrow questions with a logistic regression fit: Jev **95.0%** vs Haiku **93.2%** (not statistically significant, p=0.063). Pre-registered zero-shot benchmark: **95.9%** across 400 items.
- Calibration out-of-distribution: **ECE 0.107**, 4.4× the 0.024 noise floor. On public benchmarks 0.024–0.032 ECE, which the author reads as suggesting training-set contamination.
- Directionality: yes/no answers **underconfident** (temperature refit 0.66); choice and score answers **overconfident** (temperature 3.29–3.40).
- Worst failure: on a question it could not know the answer to, Jev was right **44.7%** of the time at an average probability of **0.74**.
- Cost per 1,000 decisions on the phishing task: Jev **$0.038**; Haiku single question **$0.462** (12×); Haiku five signals **$1.02** (27×).
- Latency measured from France: Jev **239ms** vs Haiku **687ms**.

**3. Good Start Labs, via Langfuse** ([Langfuse](https://langfuse.com/blog/2026-09-18-using-typesafes-jev-for-evals)) — 6,003 rubric checks: "$160 per million graded answers" (Jev) vs "$33,000" (Claude Fable 5.1); "91.5% agreement" with Fable 5.1; "20 to 200x faster."

**4. Every (Mike Taylor)** — described as "the one independent test published so far" at the time of the OpenTweet writeup ([OpenTweet](https://opentweet.io/jev/vs-gpt)); the documentation-classification figure "777 judgments in 0.7 seconds" for ~"$0.00025" is attributed to Every's test ([Firecrawl](https://www.firecrawl.dev/blog/what-is-jev)).

### Open questions flagged by commentators

Whether an independent benchmark confirms the claimed accuracy parity, and whether the pricing holds once the launch subsidy ends. ([OpenTweet](https://opentweet.io/jev/vs-gpt)) At launch, demand was high enough that "the company briefly lost the ability to serve users from its API." ([reported via launch coverage search;](https://techcrunch.com/2026/09/18/a-new-kind-of-ai-model-from-a-chatgpt-inventor-is-thrilling-developers/) see also [explainx.ai](https://www.explainx.ai/blog/typesafe-ai-jev-system-one-models-launch-2026))

---

## Limitations

### Hard capability boundaries (vendor-documented)

- **No text generation at all.** "Jev gives up string generation, it's optimized for structured outputs" ([typesafe.ai blog](https://typesafe.ai/blog/introducing-system-one-models-and-jev)); "Jev generates no text at all," making it unsuitable for writing code, emails, or summaries ([DataCamp](https://www.datacamp.com/blog/system-one-models-jev)). System One models "do not write replies, produce code, or generate reasoning explanations" ([docs.typesafe.ai/concepts/system-one](https://docs.typesafe.ai/concepts/system-one)).
- **Output types must be pre-declared.** Every answer is constrained to a `noul`, `choice`, or `score` defined in the request. ([docs.typesafe.ai/api](https://docs.typesafe.ai/api))
- **Cardinality caps.** `choice`: up to **255 options**. `score`: **2–10** ordered levels. ([docs.typesafe.ai/api](https://docs.typesafe.ai/api), [typesafe.ai blog](https://typesafe.ai/blog/introducing-system-one-models-and-jev))
- **Text-only input.** "Images, audio, and video are not supported." ([docs.typesafe.ai/concepts/state](https://docs.typesafe.ai/concepts/state))
- **Language.** English primary; "other languages, including CJK scripts, are accepted but currently have lower accuracy." ([docs.typesafe.ai/concepts/state](https://docs.typesafe.ai/concepts/state))
- **No rationale / audit trail.** Returns probabilities only, with no natural-language explanation of *why* it scored a case — so it cannot satisfy compliance requirements needing written justification. ([DataCamp](https://www.datacamp.com/blog/system-one-models-jev), [Langfuse](https://langfuse.com/blog/2026-09-18-using-typesafes-jev-for-evals))
- **No external context.** "Jev only evaluates the state you pass in" — it cannot fetch outside context. ([docs.typesafe.ai](https://docs.typesafe.ai/), as surfaced in docs-site search)
- **Context budget.** 64k tokens per request; 32k for state + longest question. ([docs.typesafe.ai/models](https://docs.typesafe.ai/models))
- **No weights, no self-hosting.** Hosted API only; no parameter count published. ([MarkTechPost](https://www.marktechpost.com/2026/09/19/typesafe-ai-releases-jev/))

### "Can't hallucinate" — what it actually means

TypeSafe's own framing: "'Zero hallucinations' means schema matching is guaranteed. The 0% figure is not empirical. Answers can still be wrong." ([MarkTechPost](https://www.marktechpost.com/2026/09/19/typesafe-ai-releases-jev/)) The most-replied Hacker News comment made the same point: it can't emit an invalid type, but "it can still emit a completely wrong valid value." ([HN 49717558](https://news.ycombinator.com/item?id=49717558)) Similarly, **calibration ≠ correctness**: high confidence only means that predictions grouped at higher probabilities are correct more often, not that any individual answer is right. ([gist](https://gist.github.com/pjburnhill/adf8d28efcad9df037bfdece178ef965))

### The nine documented weaknesses ("jaggedness") for Jev 1.13

From [docs.typesafe.ai/model-jaggedness/jev-1.13](https://docs.typesafe.ai/model-jaggedness/jev-1.13):

1. **Literal reading** — answers the written question, taking scoping words, negations, and implied conditions at face value. *Mitigation: "State the exact condition in the `instructions`. Be specific. Put boundary cases in the criteria."*
2. **Math and numbers** — recognizes answer shapes rather than calculating; errors grow with counting scope; numeric representations underperform semantic ones. *Mitigation: "Keep the arithmetic in code."*
3. **Date and time comparison** — "Jev reads dates as text, not as ordered quantities"; worse with mixed formats, relative references, and domain boundaries (quarters, settlement windows, accrual periods). *Mitigation: model extracts, code does arithmetic; use enumerated Choice options for date components.*
4. **Indirection** — multi-hop reasoning chains and double negatives reduce reliability. *Mitigation: "Write your instructions as directly as possible. When possible, identify the relevant parts of state by name."*
5. **Large irrelevant state** — "Unrelated detail acts as a distractor." Adding extra data "so it has everything" reduces accuracy. *Mitigation: "Send only the fields the question needs."*
6. **Adversarial content** — "Jev treats the state as data, not as hostile"; injected instructions, misleading framing, or an argument for its own classification can move the answer. *Mitigation: "Be explicit in the criteria. Test your integration thoroughly before deploying it to many users."*
7. **Contradictory instructions and criteria** — conflicting guidance or overlapping categories break it. *Mitigation: align instructions and criteria with precise language; taxonomies should pass a "two competent people agree" test ([RedHub](https://blog.redhub.ai/jev-ai-limits)).*
8. **Structural invariants not guaranteed** — P(noul) ≠ 1 − P(not noul); complementary probabilities across separate questions do not structurally sum to 1.0. *Mitigation: use a single Choice question rather than deriving invariants across questions; don't carry thresholds between question types.*
9. **Generation** — not trained for it; ineffective and slow. *Mitigation: "Turn extraction into a Choice over the options rather than asking for the value itself," or use a generative model.*

Additional, widely reported: **Jev cannot abstain.** "A forced binary with no unknown or needs_review option makes Jev pick the least wrong answer instead of saying it does not know." ([docs.typesafe.ai](https://docs.typesafe.ai/) via search; [Langfuse](https://langfuse.com/blog/2026-09-18-using-typesafes-jev-for-evals)) The independent beri.net study recommends adding an explicit "none of these" option to every choice. ([beri.net](https://www.beri.net/article/typesafe-jev-typed-decision-model-calibration-decomposition-shadow-eval))

### Calibration caveats to carry into the skill

- Confidence "is a margin, not a probability that the answer is right." ([docs.typesafe.ai/confidence](https://docs.typesafe.ai/confidence))
- Independent measurement shows ECE 0.107 out-of-distribution (4.4× noise floor), yes/no underconfident and choice/score overconfident, and 44.7% accuracy at 0.74 average probability on unknowable questions. ([beri.net](https://www.beri.net/article/typesafe-jev-typed-decision-model-calibration-decomposition-shadow-eval))
- Armin Ronacher's caution in launch coverage: users must interpret confidence scores carefully, understanding that a 50% probability indicates unreliability. ([TechCrunch](https://techcrunch.com/2026/09/18/a-new-kind-of-ai-model-from-a-chatgpt-inventor-is-thrilling-developers/))

### Pre-production checklist recommended by the independent reviewer

([beri.net](https://www.beri.net/article/typesafe-jev-typed-decision-model-calibration-decomposition-shadow-eval))

1. Test on your own labeled data (1,000–2,000 examples minimum).
2. Calibrate **per question**, not per model.
3. Add an explicit "none of these" option to every choice.
4. Use only the high-confidence band (e.g. 0.99) for full automation; route uncertain cases to an LLM fallback.
5. Run injection testing before deploying as a guardrail.
6. **Pin the version** (`jev-1.13.0`) rather than using `jev-latest`, to prevent silent calibration drift.

### Explicit "do not use Jev for" list

- Prose, chat replies, code, summaries — use an LLM. ([DataCamp](https://www.datacamp.com/blog/system-one-models-jev))
- Exact logic — math, date comparisons, counts, fixed rules — use ordinary code. ([docs.typesafe.ai/model-jaggedness/jev-1.13](https://docs.typesafe.ai/model-jaggedness/jev-1.13))
- Anything needing a written reasoning trace for audit. ([DataCamp](https://www.datacamp.com/blog/system-one-models-jev))
- Anything requiring retrieval of context outside the submitted state. ([docs.typesafe.ai](https://docs.typesafe.ai/))
- It is "not a drop-in replacement for an LLM" — it is a specialized classifier for specific decision points inside a larger architecture. ([LangChain blog](https://www.langchain.com/blog/building-a-harness-with-jev))

### Community criticism worth acknowledging

- "Just a really smart switch statement" — Nathan Flurry, one of the most-shared reactions of launch week. ([reported in launch coverage search results;](https://www.firecrawl.dev/blog/what-is-jev) see also [HN thread](https://news.ycombinator.com/item?id=49717558))
- Commenters argued comparing a specialized classifier to a general-purpose model is category error: "It's nothing like a traditional LLM and so should not be compared to one." ([HN 49717558](https://news.ycombinator.com/item?id=49717558))
- Skepticism that similar functionality was achievable with BERT years ago, and objection to it being closed-source. ([HN 49717558](https://news.ycombinator.com/item?id=49717558))
- The Doom demo used structured game state rather than raw pixels, making the speed comparison less meaningful. ([HN 49717558](https://news.ycombinator.com/item?id=49717558))
- Founder (HN handle `CompleteSkeptic`) conceded the LLM token comparison is "hard to understand" and positioned System One as complementary, not competitive, to general LLMs. ([HN 49717558](https://news.ycombinator.com/item?id=49717558))

### Research gaps — what is NOT publicly documented as of 2026-09-22

- Model weights, parameter count, and architecture details beyond "transformer-based." ([MarkTechPost](https://www.marktechpost.com/2026/09/19/typesafe-ai-releases-jev/))
- Training/calibration data beyond "exclusively synthetic." No dataset composition published. ([TechCrunch](https://techcrunch.com/2026/09/18/a-new-kind-of-ai-model-from-a-chatgpt-inventor-is-thrilling-developers/))
- Official calibration curves / ECE data — RedHub notes TypeSafe had not published these as of its article date. ([RedHub](https://blog.redhub.ai/jev-ai-limits))
- Fine-tuning or customer-specific calibration APIs — none found.
- SLA / uptime guarantees — none found.
- Enterprise pricing tiers beyond "Higher limits are available for enterprise customers." ([docs.typesafe.ai/models](https://docs.typesafe.ai/models))

---

## Sources

**TypeSafe AI official**
- https://typesafe.ai/blog/introducing-system-one-models-and-jev
- https://docs.typesafe.ai/
- https://docs.typesafe.ai/concepts/system-one
- https://docs.typesafe.ai/concepts/state
- https://docs.typesafe.ai/confidence
- https://docs.typesafe.ai/api
- https://docs.typesafe.ai/models
- https://docs.typesafe.ai/patterns
- https://docs.typesafe.ai/model-jaggedness/jev-1.13
- https://docs.typesafe.ai/llms.txt
- https://docs.typesafe.ai/llms-full.txt
- https://console.typesafe.ai/playground
- https://github.com/typesafe-ai
- https://github.com/typesafe-ai/typesafe-sdk-python
- https://github.com/typesafe-ai/typesafe-sdk-js
- https://github.com/typesafe-ai/skills
- https://github.com/typesafe-ai/system-one-adapter-python

**Press coverage**
- https://techcrunch.com/2026/09/18/a-new-kind-of-ai-model-from-a-chatgpt-inventor-is-thrilling-developers/
- https://www.tomshardware.com/tech-industry/artificial-intelligence/typesafe-ais-jev-offers-an-alternative-to-llms-that-claims-to-be-193x-faster-and-445x-cheaper-system-one-type-model-is-bespoke-for-probabilistic-decision-making
- https://www.marktechpost.com/2026/09/19/typesafe-ai-releases-jev/
- https://www.explainx.ai/blog/typesafe-ai-jev-system-one-models-launch-2026

**Practitioner / vendor-integration writeups**
- https://www.langchain.com/blog/building-a-harness-with-jev
- https://www.datacamp.com/blog/system-one-models-jev
- https://langfuse.com/blog/2026-09-18-using-typesafes-jev-for-evals
- https://www.firecrawl.dev/blog/what-is-jev
- https://pydantic.dev/docs/ai/models/typesafe/
- https://developers.cloudflare.com/ai/models/typesafe/jev/
- https://docs.litellm.ai/docs/pass_through/typesafe
- https://openrouter.ai/docs/guides/community/typesafe-sdk
- https://gist.github.com/pjburnhill/adf8d28efcad9df037bfdece178ef965

**Independent evaluation and criticism**
- https://github.com/4esv/jev-eval
- https://www.beri.net/article/typesafe-jev-typed-decision-model-calibration-decomposition-shadow-eval
- https://opentweet.io/jev/vs-gpt
- https://blog.redhub.ai/jev-ai-limits
- https://news.ycombinator.com/item?id=49717558 (the launch thread)

**Ecosystem catalogue**
- https://github.com/yibie/awesome-jev

**Provenance note.** All URLs above were used for content in this document. Most were fetched and read directly. Three were cited from search-result summaries rather than a direct fetch, and a later writer should re-verify before quoting them verbatim: `docs.litellm.ai/docs/pass_through/typesafe`, `openrouter.ai/docs/guides/community/typesafe-sdk`, and the `docs.typesafe.ai/` site root (used only for the "cannot abstain," "only evaluates the state you pass in," and "$0.0004 per decision" points — the last of which is independently corroborated by the OpenTweet benchmark writeup). Two HN sub-thread URLs surfaced in search (`item?id=49731282`, `item?id=49767192`) were **not** used and are deliberately omitted.
