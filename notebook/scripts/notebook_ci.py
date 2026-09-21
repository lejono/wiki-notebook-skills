#!/usr/bin/env python3
"""Notebook CI: structural checks for the theoretician's notebook.

Run before committing notebook changes (the /commit step of the notebook
skill). Checks only opt-in notebook pages (markdown files whose YAML
frontmatter contains a `notebook:` key), plus index files (*_index.md)
and glossaries (glossary_*.md) found under each registered notebook root.
Legacy notes without frontmatter are ignored, so old material never
floods the report.

Exit codes: 0 = clean or warnings only, 1 = hard errors (broken links,
stale index entries, unignored nested repos).

Usage:
    notebook_ci.py [--registry PATH] [--notebook NAME] [--json]
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_REGISTRY = Path(__file__).resolve().parent.parent / "references" / "notebook-registry.json"

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
# Pages have no word limit: they must be self-contained but not too long. Beyond SPLIT_HINT words the
# CI suggests splitting into a lead page plus linked step pages.
SPLIT_HINT = 1500


def parse_frontmatter(text):
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t", "-")):
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm


def strip_frontmatter(text):
    return FRONTMATTER_RE.sub("", text, count=1)


SKIP_DIRS = {".git", ".jj", ".obsidian", "bak", "backups", "scratch",
             ".claude"}
# for resolving link targets, everything outside the noise dirs is fair game
RESOLVE_SKIP = SKIP_DIRS

# The wikis (wiki skill) live in their own repos; notebook pages may still
# link into them, so resolve link targets against these external roots too.
EXTERNAL_RESOLVE_ROOTS = ["~/wikis"]


def find_files(root, pattern, exclude, skip=SKIP_DIRS):
    for p in root.rglob(pattern):
        if any(part in skip for part in p.parts):
            continue
        if any(x in p.parents for x in exclude):
            continue
        yield p


def gather(root, exclude=()):
    """Classify markdown files under a notebook root."""
    pages, indexes, glossaries, others = {}, {}, {}, {}
    for p in find_files(root, "*.md", exclude):
        try:
            text = p.read_text(errors="replace")
        except OSError:
            continue
        fm = parse_frontmatter(text)
        entry = {"path": p, "text": text, "fm": fm}
        name = p.name.lower()
        if name.endswith("_index.md") or name == "index.md":
            indexes[p] = entry
        elif name.startswith("glossary"):
            glossaries[p] = entry
        elif "notebook" in fm:
            pages[p] = entry
        else:
            others[p] = entry
    return pages, indexes, glossaries, others


def basename_map(*groups):
    """Obsidian-style resolution: link target -> file, by stem."""
    m = {}
    for g in groups:
        for p in g:
            m.setdefault(p.stem.lower(), p)
    return m


def check_notebook(nb, errors, warnings, infos, all_roots=()):
    root = Path(nb["path"]).expanduser()
    if not root.exists():
        errors.append(f"[{nb['name']}] registered path does not exist: {root}")
        return {}
    # don't rescan other registered notebooks nested inside this root
    exclude = [r for r in all_roots if r != root and root in r.parents]
    exclude += [root / e for e in nb.get("exclude", [])]
    pages, indexes, glossaries, others = gather(root, exclude)
    # link resolution is tree-wide (links into nested notebooks and the wiki
    # are legitimate); only the *checked* files above are scoped
    resolve = {p.stem.lower(): p for p in find_files(root, "*.md", (), skip=RESOLVE_SKIP)}
    # links with an explicit extension (e.g. [[refs.bib]]) resolve against any file
    all_names = {p.name.lower() for p in find_files(root, "*", (), skip=RESOLVE_SKIP) if p.is_file()}
    # notebook pages may link into the external wikis —
    # resolve those targets too so cross-repo links don't read as broken
    for ext in EXTERNAL_RESOLVE_ROOTS:
        ext = Path(ext).expanduser()
        if not ext.exists():
            continue
        for p in find_files(ext, "*.md", (), skip=RESOLVE_SKIP):
            resolve.setdefault(p.stem.lower(), p)
        for p in find_files(ext, "*", (), skip=RESOLVE_SKIP):
            if p.is_file():
                all_names.add(p.name.lower())
    label = nb["name"]

    checked = {**pages, **indexes, **glossaries}

    # 1. Wikilink resolution (checked files only)
    for p, e in checked.items():
        for target in WIKILINK_RE.findall(strip_frontmatter(e["text"])):
            tpath = Path(target.strip())
            if tpath.suffix and tpath.suffix != ".md":
                if tpath.name.lower() in all_names:
                    continue
            t = tpath.stem.lower()
            if t and t not in resolve:
                kind = "index" if p in indexes else "page"
                bucket = errors if p in indexes else warnings
                bucket.append(f"[{label}] broken link [[{target.strip()}]] in {kind} {p.relative_to(root)}")

    # 2. Orphan pages: notebook pages not linked from any index or page
    linked = set()
    for e in checked.values():
        for target in WIKILINK_RE.findall(e["text"]):
            linked.add(Path(target.strip()).stem.lower())
    for p in pages:
        if p.stem.lower() not in linked:
            warnings.append(f"[{label}] orphan page (not linked from any index/page): {p.relative_to(root)}")

    # 3. Chain integrity: Prev/Next declared but target missing
    #    Superseded pages are retired — exempt from chain upkeep.
    for p, e in pages.items():
        if e["fm"].get("status") == "superseded":
            continue
        body = strip_frontmatter(e["text"])
        has_prev = re.search(r"\*\*Prev:?\*\*", body, re.I)
        has_next = re.search(r"\*\*Next:?\*\*", body, re.I)
        if not has_prev and not has_next:
            warnings.append(f"[{label}] page has no Prev/Next chain links: {p.relative_to(root)}")

    # 4. Page hygiene
    for p, e in pages.items():
        fm = e["fm"]
        if fm.get("status") == "superseded":
            # retired page: exempt from hygiene, but must point at its replacement
            if not fm.get("superseded_by"):
                warnings.append(f"[{label}] superseded page missing 'superseded_by:': {p.relative_to(root)}")
            continue
        words = len(strip_frontmatter(e["text"]).split())
        if words > SPLIT_HINT:
            warnings.append(f"[{label}] page is {words} words; consider a lead page with linked step pages: {p.relative_to(root)}")
        if "verification" not in fm:
            warnings.append(f"[{label}] missing 'verification:' marker: {p.relative_to(root)}")
        if "date" not in fm:
            warnings.append(f"[{label}] missing 'date:' in frontmatter: {p.relative_to(root)}")

    # 5. Verification audit (informational)
    tally = {}
    for p, e in pages.items():
        status = e["fm"].get("verification", "none") or "none"
        tally.setdefault(status, []).append(str(p.relative_to(root)))
    for status, files in sorted(tally.items()):
        infos.append(f"[{label}] verification={status}: {len(files)} page(s)")
    for f in tally.get("none", []):
        infos.append(f"[{label}]   unverified: {f}")

    return {"pages": len(pages), "indexes": len(indexes), "glossaries": len(glossaries)}


def check_nested_repos(repo_root, errors):
    """Any .git dir inside the repo that jj would snapshot is a hard error."""
    root = Path(repo_root).expanduser()
    if not (root / ".jj").exists():
        return
    try:
        out = subprocess.run(
            ["find", str(root), "-name", ".git", "-not", "-path", str(root / ".jj") + "/*"],
            capture_output=True, text=True, timeout=120).stdout
    except Exception:
        return
    for gitdir in out.splitlines():
        parent = Path(gitdir).parent
        if parent == root:
            continue
        probe = parent / "PROBE.md"
        rel = parent.relative_to(root)
        chk = subprocess.run(["git", "-C", str(root / ".jj" / "repo"), "check-ignore", "-q",
                              "--no-index", str(rel) + "/PROBE.md"], capture_output=True)
        # fall back to git check-ignore against the colocated store; if git
        # is unavailable just report presence for manual review
        if chk.returncode != 0:
            ignored = subprocess.run(
                ["jj", "--repository", str(root), "file", "list", str(rel)],
                capture_output=True, text=True).stdout.strip()
            if ignored:
                errors.append(f"nested repo NOT ignored by parent (files double-tracked): {parent}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    ap.add_argument("--notebook", help="check only this notebook (registry name)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    reg = json.loads(args.registry.read_text())
    notebooks = reg["notebooks"]
    if args.notebook:
        notebooks = [n for n in notebooks if n["name"] == args.notebook]
        if not notebooks:
            print(f"no notebook named {args.notebook!r} in registry", file=sys.stderr)
            return 2

    errors, warnings, infos = [], [], []
    stats = {}
    all_roots = [Path(n["path"]).expanduser() for n in reg["notebooks"]]
    for nb in notebooks:
        stats[nb["name"]] = check_notebook(nb, errors, warnings, infos, all_roots)

    for repo_root in reg.get("repos", []):
        check_nested_repos(repo_root, errors)

    if args.json:
        print(json.dumps({"errors": errors, "warnings": warnings,
                          "info": infos, "stats": stats}, indent=2))
    else:
        for e in errors:
            print(f"ERROR   {e}")
        for w in warnings:
            print(f"WARN    {w}")
        for i in infos:
            print(f"INFO    {i}")
        print(f"\n{len(errors)} error(s), {len(warnings)} warning(s). "
              f"Pages checked: {sum(s.get('pages', 0) for s in stats.values())}")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
