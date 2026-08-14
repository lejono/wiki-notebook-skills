# Research wiki and notebook skills

Two [Claude Code](https://claude.com/claude-code) skills for keeping research knowledge in plain markdown that an agent maintains and reads selectively:

- **wiki**: the verified source of truth, following [Karpathy's LLM wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). Interlinked pages with verification labels, which the agent ingests into, queries, and lints (`wiki/scripts/wiki_ci.py`). References are fetched from INSPIRE-HEP or Crossref, never from model memory (`wiki/scripts/bib_add.py`).
- **notebook**: the theoretician's lab book. The unverified working record of calculations in progress, ideas, and dead ends, with its own structural checks (`notebook/scripts/notebook_ci.py`). Results are promoted to the wiki once verified.

Pages are markdown with LaTeX, best read in an editor that renders equations, such as [Obsidian](https://obsidian.md).

To use: copy `wiki/` and `notebook/` into `~/.claude/skills/` and point the registry files under `*/references/` at your own directories (the ones here are skeleton examples). Both skills refer to a domain-specific calculation skill (conventions, verification checklists, handoff templates); ours is too domain-specific to be useful to others, so write your own for your field.
