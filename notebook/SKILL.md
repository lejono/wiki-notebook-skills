---
name: notebook
description: "The theoretician's lab notebook — records ongoing research discussions, calculations-in-progress, ideas, and dead ends across all physics topics. Use this skill DURING any substantive physics discussion or calculation session to write short linked notebook pages as results crystallise, and at session end to commit the notebook with jj (runs CI checks first). Trigger on: 'note this down', 'add to the notebook', 'notebook this', 'commit the notebook', '/commit' in a notes directory, 'where did we discuss X', 'what did we conclude about Y', or whenever a discussion produces a result, decision, or dead end worth remembering. Distinct from the wiki skill: the wiki is the verified source of truth; the notebook is the unverified working record. If content is verified and significant, it belongs in the wiki (use /wiki ingest); everything else from a research session belongs here."
---

# Notebook Skill

The Notebook is a theoretician's lab book. It records discussions, working
calculations, hunches, and dead ends. It should be accurate and kept up to
date, but it is **not a source of truth** — pages may contain mistakes, and
nothing in it should be cited as established without checking its
verification marker.

**Notebook vs Wiki**

|              | Notebook (this skill)                                   | Wiki (`wiki` skill)                                     |
| ------------ | ------------------------------------------------------- | ------------------------------------------------------- |
| Content      | Discussions, ideas, calculations in progress, dead ends | Verified results, literature synthesis                  |
| Reliability  | May contain errors; marked by verification level        | Source of truth; could be made public                   |
| When written | During/after any research session                       | Only after verification and user approval               |
| Example      | "Today we tried X, it failed because Y"                 | "The decoherence-diffusion bound is Eq. (3) of [paper]" |

When a notebook result gets verified and matters long-term, promote it to the
wiki with `/wiki ingest` — the notebook page then links to the wiki page.

## Registry

Read `references/notebook-registry.json` (in this skill's directory) to find
the notebooks. **All notebook content lives under a single notebook root**
(e.g. `~/notes/`) — topic notebooks within it. Draft papers live in a
separate drafts root (e.g. `~/drafts/`). The registry maps names →
paths → topics. Resolve the target notebook from: explicit mention > current
working directory > conversation topic. If genuinely ambiguous, ask.

**New notebook pages ALWAYS go under the notebook root, never in the
drafts root.** The drafts root holds drafts of papers. Each draft-paper
project directory keeps a `NOTEBOOK.md` pointer to its subnotebook under the
notebook root, and each subnotebook links back to the draft paper. The
drafts root stays a registered repo (draft papers, jj-tracked) but is not
where notebook pages go — do not create notebook pages there.

Two caveats baked into the registry:
- The **wikis** are not in the notebook — they live in their own repos
  (wiki skill). The notebook may link into them; those links resolve, but
  wiki pages are never notebook pages.
- Overleaf subdirectories inside the drafts root are separate git/jj repos;
  never edit or commit them through the notebook repos.

**Placement rule: never create pages in the notebook root.** The root of a
notebook is reserved for the user's own notes. Agent-written pages go in the
relevant project directory under `<notebook>/projects/<project>/` (create the
directory and a `<project>_index.md` if the project doesn't have one yet,
and link that index from `<notebook>_index.md` or the relevant subject-area
notebook). Root-level standing files (`<notebook>_index.md`,
`glossary_<notebook>.md`) are still edited in place — the rule is about
session/topic pages.

## Standard Subnotebook Structure

Each subnotebook (`<notebook>/projects/<name>/`) holds one or more
**calculation packages** plus a few standing files. A *package* is the set of
files sharing one `<topic>` slug and one `<date>` — many packages per
subnotebook, never a single project-wide `problem.md`:

- **`<topic>_problem_<date>.md`** — self-contained problem statement, precise
  enough to hand verbatim to another LLM. Lamport-node style: the claim(s), with
  every assumption and convention explicit in the statement itself (signature,
  Fourier convention, signs, which trade-off), and what is *given* vs *to show*.
- **`<topic>_summary_<date>.md`** — the entry point: current answer, status,
  scope, caveats, links to the calculation and verification.
- **`<topic>_calculation_<date>.md`** — the derivation (split into numbered
  parts if long).
- **`<topic>_verification_<date>.md`** — tests run, with links to their scripts
  under `checks/<topic>_<date>/`.

Four standing (undated) files at the subnotebook root:

- **`<project>_index.md`** — the subnotebook index; superseded pages move to its
  `## Scratch` section.
- **`<project>_log.md`** — append-only journal; each work pass prepends a short
  dated entry (what changed, files touched/superseded, next step).
- **`handoff.md`** — snapshot of the *current* state, overwritten each session.
  Sections: Status, Verified/Provisional Results, Known Issues, Next
  Steps, Conventions, Key Files.
- **`verification-receipts.md`** — durable per-claim ledger of *how* each
  verified claim was checked (node ID, method, artefact, caveats).

Distinct roles: **log = what happened; handoff = where things stand now;
receipts = what is proven** — don't collapse them. Full layout, file roles,
artefacts, long-calculation splitting, and the supersede lifecycle are in
**`references/subnotebook-structure.md`** — read it before creating a package.

## Filenames and Dates

Kebab-case slug, ISO date **last** (not first), date also in the frontmatter:

- **`<slug>_<date>.md`** — a session/topic page.
- **`<slug>_<role>_<date>.md`** — a package file (role ∈ problem / summary /
  calculation / verification / appendix / attempts).

e.g. `markovian-limit_calculation_2026-07-10.md`. The date is when the page was
opened; don't rename to change it after edits — retire via the supersede process
in `references/subnotebook-structure.md`.

## When to Write Pages

During any substantive physics discussion, when something crystallises —
a result, a workable idea, a decision, a refuted approach — write a notebook
page for it. Don't wait to be asked, and don't wait for session end (a
crashed session loses everything). Routine chat, admin, and questions
answered straight from existing notes don't need pages.

The user's own remarks go in as `JO:` lines, verbatim:

```markdown
JO: I suspect the ultralocal limit kills this term — check next time.
```

These should be preserved and answered
## A Living Document

Never erase a mistake. We need to be able to track errors. If we started with an incorrect equation, and then find that it's wrong, don't just rewrite the notebook page with the correct equation. Instead, cross out the mistaken part ~~like this~~ and insert a dated correction. *(2026-07-10) Erratum :* ...

## Page Format

One topic per page, **~200 words** (the CI warns beyond 250). The user reads
pages in Obsidian. Every page:

```markdown
---
notebook: stochastic
date: 2026-07-02
verification: none
author: Opus 4.8
---

# Short Descriptive Title

**Up:** [[stochastic_index]] · **Prev:** [[previous-page_2026-06-28]] · **Next:** _(none yet)_

Two or three sentences of context. Then the content: what we tried, what we
found, what broke. First use of a technical term: bold it, define it in one
clause, and link it — **ultralocal limit** ([[glossary_stochastic#Ultralocal limit|glossary]]),
the limit where spatial derivative terms are dropped.

$$ S_{OM} = \tfrac{1}{2}\int (\dot\gamma - b)^2\,dt \tag{1} $$

JO: user note here if any.
```

**`author:` is whoever actually wrote the page** — the model, by name and
version (`Opus 4.8`, `GPT-5.6-sol`, `Codex/GPT-5.5`, ...). Fill it in from your
own identity; if Codex or another agent produced the derivation, name it, not
whoever pasted it in. It records provenance, not endorsement — an `author:` line
says nothing about whether the page is correct (that's `verification:`).

Equation and Obsidian/LaTeX formatting rules (no ```` ```latex ```` fences,
`$$...$$` display math, never regenerate equations — copy with `sed -n`, cite
source, `\tag{N}` numbering) are shared with the wiki skill and live in
`references/obsidian-latex.md`. Read it before writing pages with equations.

Notebook-specific navigation rules:
- Filenames: `<short-slug>_<date>.md` for session pages, `<slug>_<role>_<date>.md`
  for package files (see the Filenames and Dates section); kebab-case names for
  standing pages.
- When you finish a page that continues an earlier one, go back and set the
  earlier page's **Next:** link. Chains must be walkable both ways.

If more than ~250 words are needed, e.g. to give the answer to a posed problem, don't compress your answer (it will become unreadable), rather break up the  answer into more than one md file. E.g.. The first md file could be the executive summary of the answer, with links to each part of the answer. the other files explain each significant step  (top level Lamport node) required for the answer 

## Verification Markers

Every page carries `verification:` in its frontmatter:

- `none` — default. Unverified discussion; treat claims as provisional.
- `CAS` — key steps checked by a computer algebra system (SymPy/Mathematica).
  Link the check script (e.g. in `<notebook>/checks/`) from the page.
- `vibefeld` — verified via the append-only Lamport-node ledger of the `af`
  adversarial-formalisation tool
  ([vibefeld](https://github.com/tobiasosborne/vibefeld)). Best available.
  Link the proof structure. (A claim verified by ordinary checks keeps `CAS`
  or `none` but gets an entry on the subnotebook's
  `verification-receipts.md` page.)

Upgrade the marker only when the verification actually exists on disk —
never on the strength of "this looks right".

## Indexes (nested)

- **Master index:** `<notebook root>/notebook_index.md` — one line per
  notebook, linking to each notebook's index.
- **Notebook index:** `<name>_index.md` at each notebook root (e.g.
  `gauge_index.md`), grouping pages by subtopic.
- **Subtopic index:** when a subtopic in a notebook index exceeds ~10 pages,
  split it into `<subtopic>_index.md` and link from the parent.

Every new page gets an index entry (one line: link + hook) at the moment
it's created — not in a batch later. Every index links up to its parent.

## Glossary

Each active notebook has `glossary_<name>.md` at its root: alphabetical
`## Term` headings, one-paragraph definitions, sources if any. When a page
introduces a term not yet in the glossary: add the glossary entry, and in
the page bold the term, define it inline in one clause, and link to the
glossary heading. This is worth the friction — undefined jargon is the main
way notebooks rot. Don't invent new terminology when a standard term exists;
if you must coin a term, the glossary entry says explicitly that it's ours.

## Committing (`/commit` or "commit the notebook")

The notebook lives in one or more jj repos (the registry's `repos` list;
text files only — binaries and nested Overleaf repos are excluded via
`.gitignore`). At session end, when the user asks to
commit:

1. **Run CI:** `python3 <skill-dir>/scripts/notebook_ci.py`
   (add `--notebook <name>` to scope it). Checks: broken wikilinks, stale
   index entries, orphan pages, missing Prev/Next chains, page hygiene
   (length, `verification:`, `date:`), glossary link resolution, unignored
   nested repos, and a verification-status tally (informational).
2. **Fix errors before committing** — broken index links and unignored
   nested repos are hard failures (exit 1). Warnings are reported to the
   user but don't block.
3. **Commit each repo with changes:**
   ```bash
   cd <notebook repo>
   jj describe -m "notebook: <one-line summary of the session>"
   jj new
   ```
4. **Report:** what was committed to which repo, CI summary, and any
   verification upgrades worth doing next (pages stuck at `none` that have
   CAS-able content).

Never `jj git push` these repos anywhere without being asked — they contain
private research notes.

## Retrieval

For "where did we discuss X" / "what did we conclude about Y": start from the
relevant notebook's index, follow Prev/Next chains, and `grep -ril` the
notebook root as a fallback. Quote what the page actually says, including its
verification marker — an unverified page is recalled as "we thought", not
"we showed".
