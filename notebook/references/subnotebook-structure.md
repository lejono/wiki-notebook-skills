# Subnotebook Structure

The layout of a project subnotebook: calculation packages, standing files, the
log, artefacts, and the supersede lifecycle. Read before creating a package.

## Package model

A subnotebook holds one or more **calculation packages** plus a few standing
files. A *package* is the set of files sharing one `<topic>` slug and one
`<date>`:

```text
<project>/
├── <project>_index.md
├── <project>_log.md
├── handoff.md
├── verification-receipts.md
├── <topic>_problem_<date>.md
├── <topic>_summary_<date>.md
├── <topic>_calculation_<date>.md
├── <topic>_verification_<date>.md
├── <topic>_appendix_<date>.md        # optional
├── <topic>_attempts_<date>.md        # optional
└── checks/
    └── <topic>_<date>/
```

A subnotebook may contain **multiple problem files / packages**. Never use a
single project-wide `problem.md`.

The files of one package share the same `<topic>` and `<date>`:

```text
decoherence-bound_problem_2026-07-10.md
decoherence-bound_summary_2026-07-10.md
decoherence-bound_calculation_2026-07-10.md
decoherence-bound_verification_2026-07-10.md
```

The `<date>` is the date the calculation was **opened**. Editing a file later
does not change its date or name — retire it via *Superseding* below instead.

## File roles

| File | Role |
|------|------|
| `_problem_` | Self-contained problem statement: assumptions, conventions, given data, and what is to be shown. Lamport-node style — every assumption explicit in the statement itself. |
| `_summary_` | The entry point. Current answer, status, scope, caveats, and links to the supporting calculation and verification. |
| `_calculation_` | Readable line-by-line derivation in LaTeX. Number important equations. Split if long (see below). |
| `_verification_` | Tests performed, their outcomes, and links to the scripts/artefacts under `checks/`. |
| `_appendix_` | *(optional)* Long algebra, auxiliary lemmas, tables, alternative derivations. |
| `_attempts_` | *(optional)* Record of informative failed approaches. |

The `_summary_` is the main entry point, but **every** package file must be
linked from `<project>_index.md` and should link to its sibling package files.

## Standing files

Four undated files live at the subnotebook root:

- **`<project>_index.md`** — the subnotebook index, grouping package links by
  subtopic. Superseded pages move to its `## Scratch` section (see below). The
  CI page-checks index files.
- **`<project>_log.md`** — append-only chronological journal (see *Log*).
- **`handoff.md`** — snapshot of the *current* research state (Status, Verified/
  Provisional Results, Known Issues, Next Steps, Conventions, Key Files),
  overwritten in place each session.
- **`verification-receipts.md`** — durable per-claim ledger of *how* each
  verified claim was checked (node ID, method, artefact, outcome/caveats).

The three journals are **distinct — do not collapse them**:

> **log** = what happened over time &nbsp;·&nbsp; **handoff** = where things
> stand now &nbsp;·&nbsp; **receipts** = what is proven.

`log`, `handoff`, and `receipts` are ledgers, not dated pages: they carry no
page frontmatter (`notebook:` / `date:` / `verification:`) and the CI does not
page-check them.

## Log

`<project>_log.md` is the project's append-only journal. Each **pass** — a work
session, or a distinct round of edits — prepends one short entry, newest at top:

```markdown
## 2026-07-10 — pass 3
Re-derived the bound with the corrected (2π) factor; superseded
`decoherence-bound_calculation_2026-07-08`. Verified m→0 limit (CAS).
Next: extend to the non-Markovian kernel.
```

Keep entries to a few lines: what changed, which package files were created or
superseded, and the next step. **Never edit past entries** (living-document
rule). The log complements `handoff.md` — handoff is rewritten to the present;
the log preserves the trail.

## Calculation artefacts

CAS scripts, numerical checks, generated data, and other non-Markdown artefacts
go under:

```text
checks/<topic>_<date>/
```

For example:

```text
checks/decoherence-bound_2026-07-10/
├── residual_check.py
├── dimensional_check.wls
├── limiting_cases.ipynb
└── output/
```

Link each artefact from the package's `_verification_` page. **Do not mark a
claim verified unless the stated check exists and has actually been run.**

## Long calculations

Do not compress a calculation to meet the page-length limit. Split it into
numbered parts sharing the topic and date:

```text
decoherence-bound_calculation-01_2026-07-10.md
decoherence-bound_calculation-02_2026-07-10.md
decoherence-bound_calculation-03_2026-07-10.md
```

The `_summary_` page links the parts in order.

## Superseding a file

A normal edit keeps the filename and date. When a package file (or a whole
package) is **retired** — replaced by a newer pass, or found wrong — do **not**
rename or move it. Instead:

1. **Frontmatter:** add
   ```yaml
   status: superseded
   superseded_by: <replacement stem>   # or a short note if simply abandoned
   ```
2. **Body:** keep the content. Add a dated pointer with a walkable link, e.g.
   `*(2026-07-14) Superseded by [[decoherence-bound_calculation_2026-07-14]].*`
   If the file was *wrong* (not merely replaced), strike through the mistaken
   part `~~like this~~` and add a dated erratum — the living-document rule.
3. **Index:** move the page's link out of its subtopic group into a `## Scratch`
   section at the bottom of `<project>_index.md`. "Scratch" is a **section
   heading in the index, not a directory** — a `scratch/` directory is skipped
   by the CI and would break its links.
4. **Log:** add a line to `<project>_log.md` recording the supersession.

Superseded pages stay linked (from Scratch) and keep their frontmatter; the CI
exempts them from page-hygiene and Prev/Next-chain warnings, and warns if one
lacks `superseded_by`.

## Filenames and dates

Kebab-case descriptive slug, ISO date **last**, date also in the frontmatter:

```text
<slug>_<date>.md            # a session/topic page
<slug>_<role>_<date>.md     # a package file (role ∈ problem/summary/
                            #   calculation/verification/appendix/attempts)
```

Examples:

```text
markovian-limit_2026-07-10.md
markovian-limit_problem_2026-07-10.md
markovian-limit_calculation-02_2026-07-10.md
```

Do not rename to change the date after edits; retire via *Superseding* above.

## Which checks to run

For *which* verification checks belong on a `_verification_` page, use
whatever taxonomy your domain's verification workflow defines — at minimum:
dimensional analysis, limiting cases, symmetry checks, CAS re-derivation of
key steps, and independent numerics where applicable.
