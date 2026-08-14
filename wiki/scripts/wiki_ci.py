#!/usr/bin/env python3
"""Wiki CI: structural checks for a verified wiki (the stricter format in
references/verified-wiki.md). Run before committing wiki changes.

Format checked (see the wiki's README.md):
- <wiki>_index.md -> <section>_map.md -> pages (progressive disclosure)
- pages carry YAML frontmatter: section, date, verification: [Pub|JO|CAS|Agent|Unv]
- maps carry `type: map` and are exempt from verification labels
- every page/map has a **Parent:** link; pages stay under ~1000 words
- a CAS label requires a linked script under CAS/

Exit codes: 0 = clean or warnings only, 1 = hard errors.

Usage:
    wiki_ci.py [--registry PATH] [--wiki NAME] [--json]
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

DEFAULT_REGISTRY = Path(__file__).resolve().parent.parent / "references" / "wiki-registry.json"

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
WORD_LIMIT = 1000
# JO = verified by hand by the wiki's owner — swap in your own initials.
VALID_LABELS = {"Pub", "JO", "CAS", "Agent", "Unv", "Ext"}
# Ext = external reference (a quote/claim/exchange from other physicists,
# recorded for context, not a derivation done or checked here). Only used
# for an explicit "external_references" section — an exception to a private
# wiki's usual verified-only rule.
# status: is orthogonal to verification — how finished, not how checked.
# wip = incomplete/known-broken, kept for fixing; needs-research = stub to
# be researched later. Absent status = page is complete.
VALID_STATUS = {"wip", "needs-research"}

# Substring(s) marking citations into private/unpublished sources; pages
# containing them are flagged (informational) as not yet publishable.
# Customise per wiki.
PRIVATE_SOURCE_MARKERS = ["private_notes"]
SKIP_DIRS = {".git", ".jj", ".obsidian", "CAS", "verification"}
META_FILES = {"readme.md", "log.md"}  # link-checked only


def parse_frontmatter(text):
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t", "-")):
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm


def strip_frontmatter(text):
    return FRONTMATTER_RE.sub("", text, count=1)


CODE_FENCE_RE = re.compile(r"^\s*```.*?^\s*```\s*$", re.DOTALL | re.MULTILINE)

# math regions: $$...$$ first, then inline $...$
MATH_RE = re.compile(r"\$\$.*?\$\$|\$[^$\n]+\$", re.DOTALL)
# Macros from your own papers' preambles that MathJax/Obsidian won't render —
# extend this blacklist as you meet them.
_CUSTOM_MACROS = (
    "slashed tocheck mcomment tred tblue tgreen "
    "mathbbm mathbbmss"
).split()
# NOT blacklisted: \ket \bra \braket \cancel — MathJax v3 autoloads the
# braket and cancel extensions, so these render in Obsidian.
CUSTOM_MACRO_RE = re.compile(
    r"\\(?:" + "|".join(sorted(_CUSTOM_MACROS, key=len, reverse=True)) + r")(?![a-zA-Z])")


def strip_for_links(text):
    """Frontmatter, fenced code blocks and inline code are not link territory."""
    text = CODE_FENCE_RE.sub("", strip_frontmatter(text))
    return re.sub(r"`[^`\n]*`", "", text)


def parse_labels(raw):
    """'[Pub, CAS]' or 'Pub' -> ['Pub', 'CAS']"""
    if raw is None:
        return None
    return [x.strip() for x in raw.strip("[]").split(",") if x.strip()]


def walk_files(root):
    """All files under root, skipping noise dirs, never following dir symlinks."""
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            yield Path(dirpath) / f


def check_wiki(name, root, errors, warnings, infos, index_name=None):
    if not root.exists():
        errors.append(f"[{name}] registered path does not exist: {root}")
        return {}

    all_files = [p for p in walk_files(root) if p.is_file()]
    md = {p: p.read_text(errors="replace") for p in all_files if p.suffix == ".md"}

    index, maps, pages, meta = {}, {}, {}, {}
    for p, text in md.items():
        fm = parse_frontmatter(text)
        entry = {"text": text, "fm": fm}
        lname = p.name.lower()
        if lname == f"{name}_index.md" or (index_name and lname == index_name.lower()):
            index[p] = entry
        elif lname.endswith("_map.md") or (fm and fm.get("type") == "map"):
            maps[p] = entry
        elif lname in META_FILES:
            meta[p] = entry
        else:
            pages[p] = entry

    resolve = {p.stem.lower(): p for p in md}
    all_names = {p.name.lower() for p in all_files}
    checked = {**index, **maps, **pages, **meta}

    # 1. Wikilink resolution (errors in index/maps, warnings in pages/meta)
    for p, e in checked.items():
        for target in WIKILINK_RE.findall(strip_for_links(e["text"])):
            tpath = Path(target.strip())
            if tpath.suffix and tpath.suffix != ".md":
                if tpath.name.lower() in all_names:
                    continue
            t = tpath.stem.lower()
            if t and t not in resolve:
                nav = p in index or p in maps
                bucket = errors if nav else warnings
                kind = "index/map" if nav else "page"
                bucket.append(f"[{name}] broken link [[{target.strip()}]] in {kind} {p.relative_to(root)}")

    # 2. Orphans: content pages not linked from anywhere
    linked = set()
    for e in checked.values():
        for target in WIKILINK_RE.findall(e["text"]):
            linked.add(Path(target.strip()).stem.lower())
    for p in pages:
        if p.stem.lower() not in linked:
            warnings.append(f"[{name}] orphan page (not linked from any map/index/page): {p.relative_to(root)}")

    # 3. Index coverage: every map must be reachable — linked from the index
    # or from another map (sub-maps hang off their section map)
    nav_links = set()
    for e in {**index, **maps}.values():
        for target in WIKILINK_RE.findall(e["text"]):
            nav_links.add(Path(target.strip()).stem.lower())
    for p in maps:
        if p.stem.lower() not in nav_links:
            errors.append(f"[{name}] map not linked from index or any map: {p.relative_to(root)}")

    # 4. Parent links (maps and pages)
    for p, e in {**maps, **pages}.items():
        if not re.search(r"\*\*Parent:?\*\*", strip_frontmatter(e["text"]), re.I):
            warnings.append(f"[{name}] missing **Parent:** link: {p.relative_to(root)}")

    # 5. Page hygiene: frontmatter, labels, size
    for p, e in pages.items():
        rel = p.relative_to(root)
        fm = e["fm"]
        if fm is None:
            warnings.append(f"[{name}] no frontmatter (legacy page, needs migration): {rel}")
            continue
        if "date" not in fm:
            warnings.append(f"[{name}] missing 'date:' in frontmatter: {rel}")
        labels = parse_labels(fm.get("verification"))
        if labels is None:
            warnings.append(f"[{name}] missing 'verification:' label: {rel}")
        else:
            bad = [x for x in labels if x not in VALID_LABELS]
            if bad or not labels:
                errors.append(f"[{name}] invalid verification label(s) {bad or '[]'} (valid: {sorted(VALID_LABELS)}): {rel}")
            if labels and "CAS" in labels:
                body = e["text"]
                # public-wiki style: root-level CAS/; private-wiki style: per-section verification/
                cas_refs = re.findall(r"(?:CAS|verification)/[\w./-]+", body)
                if not any((root / r).exists() or (p.parent / r).exists() for r in cas_refs):
                    errors.append(f"[{name}] CAS label but no existing CAS/ or verification/ script linked: {rel}")
        status = fm.get("status")
        if status is not None and status not in VALID_STATUS:
            errors.append(f"[{name}] invalid status {status!r} (valid: {sorted(VALID_STATUS)}): {rel}")
        words = len(strip_frontmatter(e["text"]).split())
        if words > WORD_LIMIT:
            warnings.append(f"[{name}] page is {words} words (cap ~{WORD_LIMIT}): {rel}")

    # 6. Non-rendering LaTeX in math: custom source macros must be expanded
    # to standard MathJax before a page is written (see notation_index.md,
    # "Source-macro policy").
    for p, e in {**maps, **pages}.items():
        body = CODE_FENCE_RE.sub("", strip_frontmatter(e["text"]))
        body = re.sub(r"`[^`\n]*`", "", body)
        math = " ".join(MATH_RE.findall(body))
        hits = sorted({m.group(0) for m in CUSTOM_MACRO_RE.finditer(math)})
        if hits:
            warnings.append(f"[{name}] non-rendering macro(s) {hits} in math: {p.relative_to(root)}")
        if re.search(r"```\s*(latex|math)", e["text"]):
            warnings.append(f"[{name}] ```latex/math code fence (Obsidian won't render): {p.relative_to(root)}")

    # 7. Publishability: citations into private sources must eventually be
    # re-sourced to published papers or stripped.
    rn_pages, rn_cites = [], 0
    for p, e in {**maps, **pages}.items():
        n = sum(e["text"].count(mk) for mk in PRIVATE_SOURCE_MARKERS)
        if n:
            rn_pages.append(str(p.relative_to(root)))
            rn_cites += n
    if rn_pages:
        infos.append(f"[{name}] not yet publishable: {len(rn_pages)} page(s), "
                     f"{rn_cites} reference(s) to private sources")

    # 8. Verification tally (informational)
    tally = {}
    for p, e in pages.items():
        labels = parse_labels((e["fm"] or {}).get("verification")) or ["(unlabelled)"]
        for lab in labels:
            tally.setdefault(lab, []).append(str(p.relative_to(root)))
    for lab in ["Pub", "JO", "CAS", "Agent", "Unv", "(unlabelled)"]:
        if lab in tally:
            infos.append(f"[{name}] verification={lab}: {len(tally[lab])} page(s)")
    status_tally = {}
    for p, e in pages.items():
        s = (e["fm"] or {}).get("status")
        if s:
            status_tally.setdefault(s, []).append(str(p.relative_to(root)))
    for s in sorted(status_tally):
        infos.append(f"[{name}] status={s}: {len(status_tally[s])} page(s)")

    return {"index": len(index), "maps": len(maps), "pages": len(pages)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    ap.add_argument("--wiki", default="physics", help="registry name of the wiki to check")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    reg = json.loads(args.registry.read_text())
    entry = next((w for w in reg["wikis"] if w["name"] == args.wiki), None)
    if entry is None:
        print(f"no wiki named {args.wiki!r} in registry", file=sys.stderr)
        return 2

    errors, warnings, infos = [], [], []
    stats = check_wiki(args.wiki, Path(entry["path"]).expanduser(), errors, warnings, infos,
                       index_name=entry.get("index"))

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
              f"Pages: {stats.get('pages', 0)}, maps: {stats.get('maps', 0)}")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
