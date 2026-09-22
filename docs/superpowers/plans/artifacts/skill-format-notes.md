# SKILL.md format research: anthropics/skills conventions

Sources consulted:
- `anthropic-skills:skill-creator` skill (loaded via Skill tool — canonical Anthropic guidance for authoring skills)
- `https://github.com/anthropics/skills` — root README, `template/SKILL.md`, `spec/agent-skills-spec.md` (which redirects to `https://agentskills.io/specification`, the canonical normative spec)
- Real shipped example skills under `skills/` in that repo: `docx`, `pdf`, `pptx`, `mcp-builder` (directory listings + `SKILL.md` bodies)

---

## Required frontmatter

Per the normative spec (`agentskills.io/specification`, linked from `spec/agent-skills-spec.md`):

| Field | Required | Constraints |
|---|---|---|
| `name` | **Yes** | 1–64 characters. Lowercase unicode alphanumeric (`a-z`, `0-9`) and hyphens only. Must **not** start or end with a hyphen. Must **not** contain consecutive hyphens (`--`). **Must match the parent directory name exactly.** |
| `description` | **Yes** | 1–1024 characters, non-empty. Should describe both *what the skill does* and *when to use it*, and include specific keywords an agent would match on. |
| `license` | No | Short license name, or a pointer to a bundled license file (e.g. `LICENSE.txt has complete terms`). |
| `compatibility` | No | 1–500 characters. Only include if the skill has real environment requirements (target product, required system packages, network access). Spec and skill-creator both say: **most skills don't need this field.** |
| `metadata` | No | Free-form map of string → string for client-specific extra properties. Use reasonably unique keys to avoid collisions. |
| `allowed-tools` | No | Experimental. Space-separated string of pre-approved tools, e.g. `Bash(git:*) Bash(jq:*) Read`. Support varies by agent implementation. |

Minimal valid example:
```yaml
---
name: skill-name
description: A description of what this skill does and when to use it.
---
```

`name` validity examples — valid: `pdf-processing`, `data-analysis`; invalid: `PDF-Processing` (uppercase), `-pdf` (leading hyphen), `pdf--processing` (consecutive hyphens). For this project the directory will be `just-jev-it/` (or whatever the skill folder is finally named), so `name:` must equal that folder name character-for-character.

`description` guidance — good vs. poor, straight from the spec:
- Good: `Extracts text and tables from PDF files, fills PDF forms, and merges multiple PDFs. Use when working with PDF documents or when the user mentions PDFs, forms, or document extraction.`
- Poor: `Helps with PDFs.`

**skill-creator adds an important amplification not in the bare spec:** Claude currently tends to *under*-trigger skills. To counter this, make the description a little "pushy" — explicitly enumerate trigger phrases/contexts, not just a summary of capability. Example given by skill-creator: prefer *"...Make sure to use this skill whenever the user mentions dashboards, data visualization, internal metrics, or wants to display any kind of company data, even if they don't explicitly ask for a 'dashboard.'"* over a bare one-line capability statement.

The real `docx` skill's description follows this pushy pattern closely: it lists specific trigger phrases ("Word doc", "word document", ".docx", ".dotx"), enumerates secondary triggers (extracting/reorganizing content, inserting images, find-and-replace, tracked changes/comments), and closes with an explicit **negative scope** clause: *"Do NOT use for PDFs, spreadsheets, Google Docs, or general coding tasks unrelated to document generation."* — worth copying this "what it's NOT for" pattern for just-jev-it if it could be confused with an adjacent skill.

---

## Directory conventions

Spec-documented layout:
```
skill-name/
├── SKILL.md          # Required: metadata + instructions
├── scripts/          # Optional: executable code
├── references/       # Optional: documentation loaded on demand
├── assets/           # Optional: templates, resources used in output
└── ...                # any additional files/dirs
```

- `scripts/` — executable code (Python/Bash/JS are common). Should be self-contained or clearly document dependencies, include helpful error messages, handle edge cases gracefully. Scripts can be *run* without ever being loaded into context — that's the point of putting deterministic/repetitive logic there instead of inline instructions.
- `references/` — additional docs the agent reads only when needed (e.g. `REFERENCE.md`, `FORMS.md`, or domain-specific files like `finance.md`). Keep individual reference files focused/small since they cost context when loaded. For files >300 lines, skill-creator recommends adding a table of contents.
- `assets/` — static resources actually used *in the output* (templates, images/diagrams, data files/lookup tables), as opposed to `references/` which is read *by the agent*, not shipped in output.

Reference from the body: use **relative paths from the skill root**, and keep references **one level deep** from `SKILL.md` (avoid nested reference chains, e.g. a reference file that itself points to another reference file). Example spec syntax:
```markdown
See [the reference guide](references/REFERENCE.md) for details.

Run the extraction script:
scripts/extract.py
```

Progressive disclosure — the three loading levels every skill's structure should respect:
1. **Metadata** (~100 tokens): `name` + `description` — always resident in context for every installed skill.
2. **Instructions** (<5000 tokens recommended, spec) / **<500 lines** (both spec and skill-creator agree on this ceiling): the full `SKILL.md` body, loaded only once the skill activates.
3. **Resources** (unlimited, loaded only as needed): files under `scripts/`, `references/`, `assets/`.

skill-creator's added guidance: if `SKILL.md` is approaching the 500-line ceiling, add another layer of hierarchy and put **clear pointers** in the body telling the agent when/why to go read a given reference file (on-demand loading language like "if you need to fill a PDF form, read FORMS.md" rather than a bare link with no condition attached).

### Discrepancy: real shipped skills don't consistently follow the `references/` convention

Checked four real skill directories in `anthropics/skills/skills/`:

| Skill | Root contents (besides SKILL.md, LICENSE.txt) |
|---|---|
| `docx` | `scripts/` only — no reference docs at all |
| `pdf` | `reference.md` and `forms.md` sitting **directly at skill root**, *not* inside a `references/` folder — referenced from the body as bare filenames (`REFERENCE.md`, `FORMS.md`), plus `scripts/` |
| `pptx` | `scripts/` only |
| `mcp-builder` | a directory literally named `reference` (**singular**, not `references`), plus `scripts/` |

So: the spec's `references/` (plural) convention is the documented ideal and is what skill-creator also teaches, but **none of the four real Anthropic-authored example skills actually use a folder named `references/`.** Two put reference `.md` files at the skill root; one uses `reference/` singular; one has no reference material at all. Recommendation for just-jev-it: follow the spec's plural `references/` convention (it's the documented standard and the safer bet for a public submission), but don't be surprised if reviewers don't enforce it — root-level reference `.md` files are clearly an accepted pattern in practice.

Also note: every real example inspected ships a `LICENSE.txt` and sets `license: Proprietary. LICENSE.txt has complete terms`. This is not an Anthropic-internal quirk outside the spec — it's actually the normative spec's own documented example value for the `license` field (`agentskills.io/specification`, `license` field section). But it's a placeholder-style value describing a proprietary license bundled as a file, which fits Anthropic's own document-skill family; it isn't the right value for a public, open-source community submission. For just-jev-it, use a real OSS license identifier (e.g. `MIT` or `Apache-2.0`) rather than copying that literal string.

---

## Style rules

Spec says the body has **no format restrictions** — "write whatever helps agents perform the task effectively" — but recommends: step-by-step instructions, examples of inputs/outputs, common edge cases. In practice, both skill-creator and the real examples converge on a consistent house style:

- **Imperative voice** throughout ("Write a script…", "Run…", "Choose your approach by task…", "Unpack → edit → repack"). Skill-creator explicitly calls this out as the preferred form.
- **A short framing/decision table right after the frontmatter** when there's more than one way to do the task. `docx`'s body opens with a `Task | Approach` table (Create / Edit / Read → which tool to use for each) before any prose.
- **H2 section headers named by task/action**, not abstract categories — observed real headers: `## Creating with docx-js — gotchas`, `## Verify the output`, `## Editing existing documents`, `## Comments`, `## Dependencies` (docx); `## Overview`, `## Next Steps` (pdf).
- **Conditional, on-demand pointers to reference files**, stated as trigger conditions rather than a blanket "see also" — e.g. pdf's body says *"For advanced features… see REFERENCE.md"* and *"If you need to fill out a PDF form, read FORMS.md and follow its instructions"* rather than just linking it. This is the "on-demand loading language" the spec asks for, in practice.
- **Gotchas/warnings as bullet lists with a bolded lead-in phrase**, e.g. docx: `**Page size defaults to A4.** For US Letter set…`, `**Tables need dual widths:**…`. Concrete, specific, each bullet independently actionable.
- **A closing `## Dependencies` section** naming exact required external tools/packages and install notes (docx: `docx (npm, preinstalled — install only if require('docx') fails) · pandoc · LibreOffice (soffice) · pdftoppm (Poppler)`).
- **Scripts are invoked via shown shell/python commands, not pasted inline** — the body shows the exact command line to run a bundled script (`python scripts/office/soffice.py --headless --convert-to pdf output.docx`), keeping the script's own logic out of context until it actually runs.
- **Negative scoping in the description** (see frontmatter section above) to reduce false-triggering against adjacent skills.

Additional skill-creator style guidance (not obviously visible from the shipped examples alone, but stated directly as authoring philosophy):
- **Explain the *why*, not just bare commands.** Prefer reasoning ("do X because Y breaks otherwise") over unexplained ALL-CAPS `MUST`/`ALWAYS`/`NEVER`. Skill-creator calls heavy unexplained caps-lock language a "yellow flag" — reframe with reasoning where possible, and reserve true imperative enforcement language for cases that actually need it (the real `docx` skill does use bare imperative gotchas, e.g. **"Never use `\n`"**, without much "why" — so some terseness is evidently tolerated in practice for narrow technical footguns).
- **Output-format-definition pattern**, when the skill must produce a fixed structure:
  ```markdown
  ## Report structure
  ALWAYS use this exact template:
  # [Title]
  ## Executive summary
  ## Key findings
  ## Recommendations
  ```
- **Input/Output examples pattern**, under a named heading:
  ```markdown
  ## Commit message format
  **Example 1:**
  Input: Added user authentication with JWT tokens
  Output: feat(auth): implement JWT-based authentication
  ```
- **Keep it general**, not overfit to the exact test prompts used while drafting — the skill will be invoked for a long tail of phrasings, not just the examples used to write it.

---

## Checklist

**No public `CONTRIBUTING.md`, PR template, or formal submission checklist exists in `anthropics/skills`.** Checked: repo root (`.gitignore`, `README.md`, `THIRD_PARTY_NOTICES.md`, `.claude-plugin/marketplace.json`) — none of these is a contribution guide, and no `CONTRIBUTING.md` file is present. The README points contributors only to `./template` and the external spec/support docs; it does not describe a review process or acceptance criteria. Per the task brief's fallback instruction: **"not found publicly — using template + spec only."**

Given that, here is a practical pre-submission checklist synthesized from the spec + skill-creator + observed real-example conventions (this is **not** an official Anthropic reviewer checklist — it's derived, and should be treated as a strong default, not gospel):

- [ ] Skill folder name == `name:` frontmatter value, exactly (spec requires this).
- [ ] `name`: 1–64 chars, lowercase alphanumeric + hyphens only, no leading/trailing/consecutive hyphens.
- [ ] `description`: 1–1024 chars, states both *what* the skill does and *when* to use it, includes concrete trigger keywords/phrases a user would actually type, and is a little "pushy" per skill-creator (don't undersell triggering conditions).
- [ ] Description includes a negative-scope clause if the skill could be confused with an adjacent skill/tool ("Do NOT use for…").
- [ ] `license:` set to a real OSS identifier appropriate for an open-source submission (e.g. `MIT`, `Apache-2.0`) — not the spec's `Proprietary. LICENSE.txt has complete terms` sample value, which is a valid spec example but describes a proprietary/bundled-license case, and is also what Anthropic's own docx/pdf/pptx skills happen to use.
- [ ] `compatibility:` omitted unless there's a genuine environment requirement (most skills should omit it).
- [ ] `SKILL.md` body under ~500 lines / ~5000 tokens; anything larger moved into `references/`.
- [ ] Any reference file the body points to is referenced with an explicit **on-demand condition** ("if X, read Y"), not just a bare link, and reference chains stay one level deep from `SKILL.md`.
- [ ] Large reference files (>300 lines) have a table of contents.
- [ ] Bundled scripts are self-contained (or clearly state their dependencies), fail with helpful error messages, and are invoked via shown shell commands rather than pasted inline.
- [ ] Body uses imperative voice, task-named section headers, and (if the skill produces deterministic scripted work across similar prompts) bundles a `scripts/` helper rather than re-deriving the same script every invocation.
- [ ] No malicious/deceptive content; nothing that would surprise a user about the skill's actual behavior given its description ("Principle of Lack of Surprise" per skill-creator).
- [ ] Validate frontmatter mechanically if possible: the spec names a reference validator, `skills-ref validate ./my-skill` (from `https://github.com/agentskills/agentskills/tree/main/skills-ref`) — not verified installed in this environment, but worth trying before submission.
