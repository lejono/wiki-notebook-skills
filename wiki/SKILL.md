---
name: wiki
description: "Maintain and query persistent markdown wikis (Karpathy LLM Wiki pattern). Use this skill whenever the user says /wiki, asks to ingest conversation results into a knowledge base, queries existing wiki content, or asks to lint/health-check a wiki. Also use it when working in a domain with a registered wiki and you need information not currently in context — but only conservatively (don't read wiki pages speculatively). Covers any wiki registered in wiki-registry.json. Trigger on mentions of 'wiki', 'ingest this', 'add to the wiki', 'check the wiki', 'lint the wiki', or when an agent needs to update its knowledge base section."
---

# Wiki Skill

A unified skill for maintaining persistent, compounding markdown wikis using the Karpathy LLM Wiki pattern. Wikis are Obsidian-compatible markdown knowledge bases with cross-references, indexes, and audit logs.

## Core Philosophy

The tedious part of maintaining a knowledge base is the bookkeeping — cross-referencing, consistency, index updates. This skill handles that. The user curates sources and decides what's worth recording; the skill handles structure, linking, and maintenance.

Wikis compound over time. Each ingest strengthens the existing synthesis rather than starting fresh.

## Wiki vs Notebook

The wiki is the **verified source of truth** — it sits atop papers and holds
checked results, literature reviews, and significant equations; it could be
made public. Unverified material — discussion notes, calculations in
progress, ideas, dead ends — belongs in the **Notebook** (see the `notebook`
skill), not here. Do not ingest unverified session results into a wiki;
write them as notebook pages and promote them here only once verified and
approved.

## Registry

Read `references/wiki-registry.json` (in this skill's directory) to discover available wikis. Each entry has:
- `name` — short identifier for targeting (e.g. "physics")
- `path` — filesystem path to the wiki root
- `index` — filename of the wiki's index/TOC
- `maintainer` — "user", an agent name, or "hybrid"
- `topics` — keywords for matching context to wiki

To add a new wiki, update the registry file. No code changes needed.

## Operations

### 1. Ingest (`/wiki ingest`)

Add new content to a wiki and update its index.

**Modes:**
- `/wiki ingest this` — Extract key results from the current conversation. Propose wiki entries for approval before writing.
- `/wiki ingest <path>` — Read the specified file, create/update wiki pages, update index.
- `/wiki ingest <target> <content>` — Ingest content into a specific wiki.

**Workflow:**

1. **Identify target wiki.** Use explicit target if given; otherwise infer from conversation topic, cwd, or content. If ambiguous, ask.
2. **Read the wiki's current index** to understand existing structure and avoid duplicates.
3. **Store source files.** When ingesting an external paper (arxiv, published), download the source `.tex` files and store them in the wiki's associated literature folder, e.g. `literature/<author-year-short-title>/`. This ensures equations can be extracted with `sed -n` in future sessions.
4. **Draft proposed pages** (or updates to existing pages). Keep each page focused on one topic, under ~100 lines.
5. **Show proposed changes** to the user. Include: new page titles, which index entries will be added, any existing pages that will be updated.
6. **On approval, write content.** Use `sed -n` to copy any LaTeX equations from source files — never regenerate equations token-by-token.
7. **Update the index** with new links.
8. **Append to `log.md`** in the wiki root: date, operation, pages affected.

**For "ingest this" (conversation results):**
- Identify genuinely novel results worth preserving (not routine chat)
- For calculations: extract key equations (numbered), derivation steps, and final results
- Write mathematical content to `.md` files (user reads in Obsidian, cannot see LaTeX in terminal)
- Each equation must cite its source of truth (paper, .tex file with line numbers)
- Accuracy rule: anything not explicitly present in a checked source is either marked `[UNVERIFIED]` or excluded, never stated flatly.

### 2. Query (`/wiki query`)

Search wiki pages and synthesize answers.

- `/wiki query "question"` — auto-detect relevant wiki(s)
- `/wiki query <target> "question"` — search specific wiki

**Workflow:**

1. **Identify relevant wiki(s)** from question context or explicit target.
2. **Read the index** to find relevant pages.
3. **Read relevant pages** (only those needed — keep context lean).
4. **Synthesize answer** from wiki content.
5. **If synthesis produced genuinely new insight**, offer to ingest it back as a new page.

**Auto-query (conservative):**
- Only auto-query when you genuinely need information not in the current context
- On first encounter of a wiki's topic domain in a session, read only the index (not full pages)
- Never auto-query during casual conversation
- When auto-querying, say so: "Checking the physics wiki for..."

### 3. Lint (`/wiki lint`)

Health-check a wiki for structural issues.

- `/wiki lint` — lint all registered wikis
- `/wiki lint <target>` — lint specific wiki

**Checks:**
- Broken `[[wikilinks]]` and markdown links (target file doesn't exist)
- Orphaned pages (exist in wiki but not linked from index or other pages)
- Stale entries (index references files that no longer exist)
- Index gaps (pages exist but aren't in the index)
- Contradictions (same claim stated differently in two places — flag for review, don't auto-fix)

**Actions:**
- Report findings to user
- Propose fixes (add missing index entries, remove stale links)
- **Dead-path repair rule:** when a referenced file no longer exists, locate the resource's *current* home (search by filename across likely roots) before repointing — never repoint to the nearest stale artifact (a `.backup`, an old copy). Resources referenced from several places get ONE canonical home plus symlinks, never copies.
- Rebuild `backlinks.md` (reverse reference map — useful for Obsidian graph view)
- On approval, apply fixes and log them

## The Verified-Wiki Tier

A wiki holding verified results benefits from a stricter format (colocated jj
repo, progressive disclosure, per-page verification frontmatter, standing
pages). Before writing pages in such a wiki, read `references/verified-wiki.md`
in this skill's directory.

### Two-tier wikis (public vs private)

For an active research programme it pays to keep **two** wikis, both their own
colocated jj repos:

```
notebook   (notebook skill)      unverified working record
    │   verify, then promote
    ▼
private wiki                     PRIVATE, verified-only — you + collaborators
    │   curate to publish-ready, then promote
    ▼
public wiki                      PUBLISHABLE — can be made public
```

- **private wiki** — verified-only results promoted up from the notebook.
  Organised by section like the public wiki, but **each section directory
  carries a `verification/` folder that is the source of truth backing its
  pages** (calculation + CAS/numeric checks + receipt or ledger) — **per
  section, not per page**. This parallels how the public wiki's `literature/`
  keeps its pages alongside their `.tex`/`.bib` sources.
- **public wiki** — the curated, publishable synthesis.

The two link both ways via relative paths (keep them siblings). Promote a
result *up* the ladder only when it clears the next tier's bar (verified →
private; publish-ready → public); never publish private material to the
public wiki without that curation step.

## Page Format

Keep pages small and focused. One topic per page. Split if exceeding ~100 lines (verified wiki: the ~1000-word CI cap governs).

**The user reads wiki pages in Obsidian**, which renders LaTeX natively in `$...$` and `$$...$$` blocks. Follow the shared Obsidian/LaTeX rules in `../notebook/references/obsidian-latex.md` (no ```` ```latex ```` fences; `$$...$$` display, `$...$` inline).

```markdown
# Title

Brief synthesis (2-3 sentences max).

## Key Results

- Result with equation reference
- Another result

## Sources

- [[source-note]] — what was extracted
- `~/path/to/paper.tex` (Eq. 3.2) — source of truth for Eq. (1)

## Chain

- Prev: [[previous-session-page]]
- Next: [[next-session-page]]

## Cross-references

- [[related-page]]
```

**Parent links:** Every page should link to its parent in the hierarchy. For example, a paper page under "Open QFT" should have `**Parent:** [[lit_open_qft_overview]]`, and that overview page should link to the Literature Reviews section of the index. This ensures navigability in Obsidian's graph view.

For calculation pages with equations:

$$
S_{OM}[\gamma] = \frac{1}{2} \int_0^T \left( \dot\gamma - b(\gamma) \right)^2 dt \tag{1}
$$

> Source: `~/papers/.../main.tex` lines 45-47

**The Chain section** is for multi-session calculation sequences. Each page links prev/next so the full derivation history is navigable. The index groups chains together.

## Adding references (`scripts/bib_add.py`)

**Never hand-write or reconstruct a BibTeX entry from memory.** A fabricated
reference costs a one-year arXiv ban. Fetch it:

```bash
python3 <skill-dir>/scripts/bib_add.py add 2407.13820           # dry run
python3 <skill-dir>/scripts/bib_add.py add 2407.13820 --write   # append
python3 <skill-dir>/scripts/bib_add.py add 10.1103/7whh-9j22    # by DOI
```

Source is INSPIRE-HEP, which keeps ONE record from preprint to publication and
so returns the arXiv eprint *and* the journal/DOI together — Crossref drops the
eprint, the arXiv API never learns the paper was published, and APS export
needs a browser. Crossref is a DOI-only fallback for papers outside INSPIRE's
(hep/gr-qc/astro-ph) coverage. Every field written is an API pass-through; the
script verifies the returned record carries the exact identifier requested and
aborts rather than guessing. Writes require `--write`.

Keys are Google Scholar style **NameYearFirstword** (`oppenheim2024emergence`),
generated automatically: leading stopwords skipped (`diosi2022there` ← "*Is
there* a relativistic…"), non-ASCII dropped rather than transliterated
(`ostrogradsky1850mmoire` ← "*Mé*moire"). Override with `--key`.

Preprints that have since been published are found by:

```bash
python3 <skill-dir>/scripts/bib_add.py refresh            # dry run
python3 <skill-dir>/scripts/bib_add.py refresh --write
```

It matches on identifier only (never title similarity), never renames a key,
fills only blank/placeholder fields, and reports conflicts for a human instead
of overwriting. `year` is only ever reported, never rewritten — a preprint year
and a publication year are both correct-for-something.

## Equation Handling

The Obsidian/LaTeX equation-formatting rules (no ```` ```latex ```` fences,
`$$...$$` display math, copy equations with `sed -n` and never regenerate,
`> Source:` citation, `\tag{N}` numbering, write to files not terminal) are
shared with the notebook skill and live in
`../notebook/references/obsidian-latex.md`. Read it before
writing pages with equations.

## Versioning and Error Handling

Preserve the record of what works and what doesn't — wrong turns are valuable.

- **Discussion/analysis notes with errors:** Never overwrite. Instead:
  1. Rename the original to `page-v1.md` (so errors are visible in file listings).
  2. Add a correction notice at the top of v1 explaining what's wrong and linking to v2.
  3. Create `page-v2.md` with the corrected analysis. Include a "What v1 got wrong" section explaining the error and what was learned.
  4. Update all wiki-links that pointed to the original to use the new `-v1` filename.
- **Factual corrections (wrong sign, typo):** Same v1/v2 pattern if the error is instructive. For trivial typos in non-discussion pages, in-place fix with a banner is fine:
  ```markdown
  > **Correction (2026-05-05):** Eq. (3) had wrong sign. Fixed from [[session-where-found]].
  ```
- **Chain invalidation:** If a later session invalidates earlier work, the earlier page gets a banner pointing to the correction.
- **Don't over-version.** Routine index updates, link fixes, and lint repairs don't need backups.

## Log Format

Each wiki maintains `log.md` — append-only, one line per operation:

```markdown
- 2026-05-05 — ingest — Added [[new-page-title]], updated index
- 2026-05-05 — lint — Fixed 3 broken links, added 2 orphans to index
```

## Target Resolution

When no explicit target is given, resolve wiki from:
1. Explicit `/wiki <op> <target>` argument
2. Current working directory (if inside a registered wiki's path)
3. Conversation topic (match against registry topics)
4. Ask the user if still ambiguous

## Adding New Wikis

To register a new wiki:
1. Update `references/wiki-registry.json` with a new entry
2. Ensure the wiki directory exists with at least an index file
3. The skill will discover it on next invocation


## Editing a wiki

From time to time, the user may ask you to edit a wiki. This will often be done by first commenting inside a wiki page, e.g. "JO: this should be moved to ....". You should make the edit, then move the comment to the wiki log, and document your change in the log.
