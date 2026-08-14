# Obsidian / LaTeX formatting rules (shared)

Shared by the `notebook` and `wiki` skills. Both write Obsidian-compatible
markdown that the user reads in Obsidian, which renders LaTeX natively in
`$...$` (inline) and `$$...$$` (display) blocks. These rules keep equations
byte-exact and renderable; keep this one file authoritative rather than
duplicating the rules in each skill.

Rules:

1. **Never regenerate LaTeX.** Use `sed -n 'N,Mp' source.tex > target.md` to copy equations between files.
2. **Always use `$$...$$` for display equations and `$...$` for inline.** Never use ```` ```latex ```` or ```` ```math ```` code fences — Obsidian doesn't render them.
3. **Always cite source.** Every equation gets a `> Source:` line with file path and line numbers.
4. **Number equations** with `\tag{N}` for in-page reference. Use hierarchical numbering for pages that sit under a parent section (e.g. `\tag{3.2}` for the 2nd equation on the 3rd page in a section). Standalone pages can use simple `\tag{1}`, `\tag{2}`.
5. **Write to files, not terminal.** Any response with non-trivial LaTeX goes to an `.md` file.

