# Verified Wiki Specifics

A wiki holding verified results has a stricter format on top of the general
wiki rules in `SKILL.md`. Keep a `README.md` in the wiki root and read it
before writing pages there. In brief:

- **Own colocated jj repo.** At session end: run
  `python3 <skill-dir>/scripts/wiki_ci.py`, fix errors, append one line to
  `log.md`, then `jj describe -m "wiki: ..." && jj new` inside the wiki.
  Never `jj git push` unless asked.
- **Progressive disclosure:** `<wiki>_index.md` → `<section>_map.md` →
  (subtopic index past ~10 pages) → pages of ≤ ~1000 words. Every new page
  gets a map entry at creation time and a `**Parent:**` link.
- **Frontmatter on every page:** `section:`, `date:`, and
  `verification:` — a list from `Pub` (copied from published result, linked),
  `JO` (verified by hand by the wiki's owner — use your own initials),
  `CAS` (real CAS script in `CAS/`, linked), `Agent` (adversarially
  agent-reviewed, no CAS artifact), `Unv` (unverified, the honest default).
  Maps use `type: map` instead of a label. Upgrade labels only when the
  artifact exists.
- **Standing pages:** `conventions.md` (canonical conventions + per-paper
  dictionary — new pages keep quoted equations verbatim in source notation
  and declare deviations), `notation_index.md`, `glossary.md` (add terms on
  first use, with source).
