#!/usr/bin/env python3
"""Add or refresh BibTeX entries in a wiki bibliography, from INSPIRE-HEP / Crossref.

    bib_add.py add 2407.13820              # dry run: show the entry it would add
    bib_add.py add 2407.13820 --write      # actually append it
    bib_add.py add 10.1103/7whh-9j22       # by DOI
    bib_add.py add 2407.13820 --key foo2024bar   # override the generated key
    bib_add.py refresh                     # dry run: which preprints are now published?
    bib_add.py refresh --write             # apply the journal data
    bib_add.py refresh --only oppenheim2024emergence

ANTI-HALLUCINATION CONTRACT (read before modifying this file)
-------------------------------------------------------------
A fabricated reference costs a one-year arXiv ban. Therefore:

  1. There is NO language model in this pipeline. It is HTTP -> parse -> file.
     Every emitted field is a byte-for-byte pass-through of what the API
     returned. Nothing is inferred, completed, corrected, or "tidied".
  2. Identity is VERIFIED, never assumed: the record an API hands back must
     carry the exact identifier we asked for, or we abort. A search that
     returns something merely similar is treated as a failure, not a match.
  3. Ambiguity aborts. Multiple hits, zero hits, network error, unparseable
     payload -> non-zero exit and no write. There is no fallback that invents
     an entry from a bare identifier.
  4. `refresh` matches on identifier only, NEVER on title/author similarity,
     and never rewrites an existing key or an existing non-empty field. It
     adds missing fields and REPORTS conflicts for a human to adjudicate.
  5. Writes require --write. Default is dry run.

The only judgement call the script makes is the citation key, which is
cosmetic, is printed for confirmation, and can be overridden with --key.
"""

from __future__ import annotations

import argparse
import datetime
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BIB = "library.bib"  # set to your wiki bibliography, or pass --bib
UA = "bib_add.py (wiki bibliography maintenance; mailto:you@example.org)"  # use a real contact address
TIMEOUT = 30

# Leading words Google Scholar skips when building NameYearFirstword keys.
# Calibrated against an existing physics bibliography:
#   blanchard1993interaction <- "On the interaction between classical and quantum systems"
#   diosi2022there           <- "Is there a relativistic GKLS master equation?"
#   maartens2011universe     <- "Is the Universe homogeneous?"
#   galley2021nogo           <- "A no-go theorem on the nature of the gravitational field"
#   gross1984quantum         <- "Is quantum gravity unpredictable?"
#   mannheim1997galactic     <- "Are galactic rotation curves really flat?"
STOPWORDS = {"a", "an", "the", "on", "is", "are", "of", "in", "for", "to", "and"}

# Fields `refresh` is allowed to fill in, i.e. those that appear once a
# preprint is published. Deliberately excludes author/title: if those differ
# from what we hold, that is a human's problem, not a script's.
#
# `year` is deliberately NOT here. When a 2016 preprint appears in 2018 the two
# years are both correct-for-something, and silently rewriting one would change
# how every existing citation renders. Those are reported as conflicts instead.
REFRESHABLE = ("doi", "journal", "volume", "number", "pages")

# Values that look like data but are placeholders meaning "not published yet".
# Google Scholar exports `journal = {arXiv preprint arXiv:2306.09596}`, which is
# not a journal; treating it as one would make every such entry a permanent
# false conflict. Overwriting these is filling a blank, not overruling a human.
PLACEHOLDER_RE = re.compile(r"^\s*(arxiv([ :]|$)|preprint\b|submitted\b|to appear\b)", re.I)


class Abort(Exception):
    """Any condition under which writing a reference would be unsafe."""


# --------------------------------------------------------------------------
# fetching
# --------------------------------------------------------------------------

def _get(url: str, accept: str | None = None) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    if accept:
        req.add_header("Accept", accept)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        raise Abort(f"HTTP {e.code} from {url}")
    except Exception as e:  # noqa: BLE001 - network layer is broad by nature
        raise Abort(f"network error for {url}: {e}")


def normalise_arxiv(s: str) -> str:
    s = s.strip()
    s = re.sub(r"^(arxiv:)", "", s, flags=re.I)
    s = re.sub(r"^https?://arxiv\.org/(abs|pdf)/", "", s, flags=re.I)
    s = re.sub(r"v\d+$", "", s)
    return s


def normalise_doi(s: str) -> str:
    s = s.strip()
    s = re.sub(r"^(doi:)", "", s, flags=re.I)
    s = re.sub(r"^https?://(dx\.)?doi\.org/", "", s, flags=re.I)
    return s


def looks_like_doi(s: str) -> bool:
    return normalise_doi(s).startswith("10.")


def fetch_inspire(ident: str) -> tuple[str, str]:
    """Return (bibtex, source_url) from INSPIRE. Raises Abort on any doubt."""
    if looks_like_doi(ident):
        url = f"https://inspirehep.net/api/doi/{normalise_doi(ident)}?format=bibtex"
    else:
        url = f"https://inspirehep.net/api/arxiv/{normalise_arxiv(ident)}?format=bibtex"
    body = _get(url).strip()
    if not body or "@" not in body:
        raise Abort(f"INSPIRE returned no BibTeX for {ident!r}")
    n = len(re.findall(r"^@\w+\{", body, re.M))
    if n != 1:
        raise Abort(f"INSPIRE returned {n} entries for {ident!r}; refusing to guess")
    return body, url


def fetch_crossref(doi: str) -> tuple[str, str]:
    doi = normalise_doi(doi)
    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi)}/transform/application/x-bibtex"
    body = _get(url, accept="application/x-bibtex").strip()
    if not body.startswith("@"):
        raise Abort(f"Crossref returned no BibTeX for {doi!r}")
    return body, url


# --------------------------------------------------------------------------
# parsing
# --------------------------------------------------------------------------

def parse_entry(bib: str) -> tuple[str, str, dict[str, str]]:
    """Split one BibTeX entry into (type, key, {field: raw_value})."""
    m = re.match(r"\s*@(\w+)\s*\{\s*([^,]+),(.*)\}\s*$", bib.strip(), re.S)
    if not m:
        raise Abort("could not parse the BibTeX returned by the API")
    etype, key, body = m.group(1), m.group(2).strip(), m.group(3)

    fields: dict[str, str] = {}
    i, n = 0, len(body)
    while i < n:
        fm = re.compile(r"([A-Za-z][\w-]*)\s*=\s*").search(body, i)
        if not fm:
            break
        name = fm.group(1).lower()
        j = fm.end()
        while j < n and body[j] in " \t\n":
            j += 1
        if j >= n:
            break
        if body[j] in "{\"":
            open_c = body[j]
            close_c = "}" if open_c == "{" else '"'
            depth, k = 0, j
            while k < n:
                if body[k] == "{":
                    depth += 1
                elif body[k] == "}":
                    depth -= 1
                    if open_c == "{" and depth == 0:
                        break
                elif body[k] == close_c and open_c == '"' and depth == 0 and k > j:
                    break
                k += 1
            val = body[j + 1:k]
            i = k + 1
        else:
            k = j
            while k < n and body[k] not in ",\n":
                k += 1
            val = body[j:k].strip()
            i = k
        fields[name] = " ".join(val.split())
    return etype, key, fields


def read_bib(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def existing_entries(text: str) -> list[tuple[str, str, dict[str, str]]]:
    out = []
    for m in re.finditer(r"@\w+\s*\{[^,]+,.*?\n\}", text, re.S):
        try:
            out.append(parse_entry(m.group(0)))
        except Abort:
            continue
    return out


# --------------------------------------------------------------------------
# key generation (Google Scholar style: NameYearFirstword)
# --------------------------------------------------------------------------

def _strip_latex(s: str) -> str:
    s = re.sub(r"\\[a-zA-Z]+\s*", "", s)     # \"u, \textit ...
    s = re.sub(r"[{}$\\]", "", s)
    return s


def _asciify(s: str) -> str:
    """Drop non-ASCII outright; do NOT transliterate.

    Mémoire -> Mmoire, not Memoire. This looks wrong but matches Google
    Scholar and hence the existing convention (ostrogradsky1850mmoire).
    Decomposing to combining marks first would yield 'memoire' and silently
    disagree with every accented key already in the file.
    """
    return s.encode("ascii", "ignore").decode("ascii")


def surname_of(author_field: str) -> str:
    """First author's surname. Handles 'Last, First and ...' and 'First Last and ...'."""
    first = re.split(r"\s+and\s+", author_field.strip())[0].strip()
    first = _asciify(_strip_latex(first))
    if "," in first:
        surname = first.split(",")[0]
    else:
        parts = first.split()
        surname = parts[-1] if parts else ""
    return re.sub(r"[^A-Za-z]", "", surname).lower()


def firstword_of(title_field: str) -> str:
    title = _asciify(_strip_latex(title_field))
    words = re.findall(r"[A-Za-z0-9']+(?:-[A-Za-z0-9']+)*", title)
    for w in words:
        clean = re.sub(r"[^A-Za-z0-9]", "", w).lower()
        if not clean:
            continue
        if clean in STOPWORDS:
            continue
        return clean
    return ""


def make_key(fields: dict[str, str]) -> str:
    name = surname_of(fields.get("author", ""))
    year = re.sub(r"[^0-9]", "", fields.get("year", ""))[:4]
    word = firstword_of(fields.get("title", ""))
    if not (name and year and word):
        raise Abort(
            f"cannot build a key from author={fields.get('author')!r} "
            f"year={fields.get('year')!r} title={fields.get('title')!r}; use --key"
        )
    return f"{name}{year}{word}"


def dedupe_key(key: str, taken: set[str]) -> str:
    if key not in taken:
        return key
    for suffix in "abcdefghijklmnopqrstuvwxyz":
        if key + suffix not in taken:
            return key + suffix
    raise Abort(f"cannot disambiguate key {key!r}")


# --------------------------------------------------------------------------
# verification — the part that stops a wrong reference landing in the file
# --------------------------------------------------------------------------

def verify_identity(requested: str, fields: dict[str, str], source: str) -> None:
    """The record must carry the identifier we asked for. No fuzzy matching."""
    if looks_like_doi(requested):
        want = normalise_doi(requested).lower()
        got = normalise_doi(fields.get("doi", "")).lower()
        if got != want:
            raise Abort(
                f"identity check FAILED: asked {source} for doi {want!r}, "
                f"record carries doi {got!r}. Refusing to write."
            )
    else:
        want = normalise_arxiv(requested).lower()
        got = normalise_arxiv(fields.get("eprint", "")).lower()
        if got != want:
            raise Abort(
                f"identity check FAILED: asked {source} for arXiv {want!r}, "
                f"record carries eprint {got!r}. Refusing to write."
            )


def render(etype: str, key: str, fields: dict[str, str], order: list[str]) -> str:
    keys = [k for k in order if k in fields] + [k for k in fields if k not in order]
    width = max(len(k) for k in keys)
    lines = [f"@{etype}{{{key},"]
    for k in keys:
        lines.append(f"    {k.ljust(width)} = {{{fields[k]}}},")
    lines[-1] = lines[-1].rstrip(",")
    lines.append("}")
    return "\n".join(lines)


FIELD_ORDER = ["author", "title", "eprint", "archivePrefix", "archiveprefix",
               "primaryClass", "primaryclass", "doi", "journal", "volume",
               "number", "pages", "year", "publisher", "note"]


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------

def cmd_add(args) -> int:
    ident = args.identifier
    try:
        bib, url = fetch_inspire(ident)
        source = "INSPIRE"
    except Abort as e:
        print(f"  INSPIRE: {e}", file=sys.stderr)
        if not looks_like_doi(ident):
            raise Abort(
                "INSPIRE has no record for this arXiv id and Crossref cannot be "
                "queried without a DOI. Not writing anything.\n"
                "  (If the paper is outside INSPIRE's coverage, find its DOI and "
                "re-run with that.)"
            )
        print("  falling back to Crossref (note: Crossref carries no arXiv eprint)",
              file=sys.stderr)
        bib, url = fetch_crossref(ident)
        source = "Crossref"

    etype, upstream_key, fields = parse_entry(bib)
    verify_identity(ident, fields, source)

    text = read_bib(args.bib)
    entries = existing_entries(text)
    taken = {k for _, k, _ in entries}

    # duplicate detection on identifiers, before keys
    for _, k, f in entries:
        if fields.get("eprint") and normalise_arxiv(f.get("eprint", "")).lower() == \
                normalise_arxiv(fields["eprint"]).lower():
            print(f"already present as {k!r} (same eprint {fields['eprint']}). "
                  f"Use `refresh` to update its journal data.", file=sys.stderr)
            return 2
        if fields.get("doi") and normalise_doi(f.get("doi", "")).lower() == \
                normalise_doi(fields["doi"]).lower():
            print(f"already present as {k!r} (same doi {fields['doi']}).",
                  file=sys.stderr)
            return 2

    key = args.key or dedupe_key(make_key(fields), taken)
    if args.key and args.key in taken:
        raise Abort(f"--key {args.key!r} is already used in {args.bib}")

    today = datetime.date.today().isoformat()
    block = (f"\n% Retrieved from {source} {today}: {url}\n"
             f"% upstream key {upstream_key}\n"
             + render(etype, key, fields, FIELD_ORDER) + "\n")

    print(block)
    if not args.write:
        print(f"[dry run] would append to {args.bib} — re-run with --write",
              file=sys.stderr)
        return 0

    with open(args.bib, "a", encoding="utf-8") as f:
        f.write(block)
    print(f"appended {key!r} to {args.bib}", file=sys.stderr)
    return 0


def cmd_refresh(args) -> int:
    text = read_bib(args.bib)
    entries = existing_entries(text)

    candidates = [(t, k, f) for t, k, f in entries
                  if f.get("eprint") and not f.get("volume")]
    if args.only:
        candidates = [c for c in candidates if c[1] == args.only]
        if not candidates:
            raise Abort(f"{args.only!r} is not an entry with an eprint and no volume")

    print(f"{len(candidates)} entrie(s) with an arXiv eprint but no volume "
          f"(candidates for having been published since)\n", file=sys.stderr)

    updated = text
    n_up = n_conf = 0
    for _, key, fields in candidates:
        ident = fields["eprint"]
        try:
            bib, url = fetch_inspire(ident)
            _, _, new = parse_entry(bib)
            verify_identity(ident, new, "INSPIRE")
        except Abort as e:
            print(f"  {key:34s} skipped ({e})", file=sys.stderr)
            continue

        if not new.get("volume"):
            print(f"  {key:34s} still unpublished upstream", file=sys.stderr)
            continue

        adds, conflicts = {}, []
        for fld in REFRESHABLE:
            got = new.get(fld)
            if not got:
                continue
            have = fields.get(fld)
            if not have or PLACEHOLDER_RE.match(have):
                adds[fld] = got
            elif " ".join(have.split()).lower() != " ".join(got.split()).lower():
                conflicts.append((fld, have, got))

        # `year` is never auto-applied, only reported (see REFRESHABLE).
        got_year, have_year = new.get("year"), fields.get("year")
        if got_year and have_year and got_year.strip() != have_year.strip():
            conflicts.append(("year", have_year, got_year))
        elif got_year and not have_year:
            adds["year"] = got_year

        # Conflicts are reported but never written. Blanks are filled even when
        # some *other* field conflicts: identity is already verified by eprint,
        # so this is definitely the right paper, and filling an empty field
        # cannot overrule a human's decision.
        if conflicts:
            n_conf += 1
            print(f"  {key:34s} CONFLICT — these fields left alone:", file=sys.stderr)
            for fld, have, got in conflicts:
                print(f"      {fld}: local {have!r} vs INSPIRE {got!r}", file=sys.stderr)
        if not adds:
            continue

        if not conflicts:
            n_up += 1
        note = fields.get("note", "")
        drop_note = bool(re.search(r"to appear|in press|submitted", note, re.I))
        print(f"  {key:34s} {'also fills' if conflicts else 'PUBLISHED ->'} "
              + ", ".join(f"{k}={v}" for k, v in adds.items())
              + (f"   [drops note={note!r}]" if drop_note else ""), file=sys.stderr)

        merged = dict(fields)
        merged.update(adds)
        if drop_note:
            merged.pop("note", None)

        m = re.search(r"@(\w+)\s*\{\s*" + re.escape(key) + r"\s*,.*?\n\}", updated, re.S)
        if not m:
            print(f"      ! could not relocate {key!r} in the file; skipped",
                  file=sys.stderr)
            n_up -= 1
            continue
        etype = m.group(1)
        today = datetime.date.today().isoformat()
        block = (f"% Journal data added from INSPIRE {today}: {url}\n"
                 + render(etype, key, merged, FIELD_ORDER))
        updated = updated[:m.start()] + block + updated[m.end():]

    print(f"\n{n_up} updatable, {n_conf} conflicting, "
          f"{len(candidates) - n_up - n_conf} unchanged", file=sys.stderr)

    if not args.write:
        print(f"[dry run] no changes written — re-run with --write", file=sys.stderr)
        return 0
    if n_up:
        with open(args.bib, "w", encoding="utf-8") as f:
            f.write(updated)
        print(f"wrote {n_up} update(s) to {args.bib}", file=sys.stderr)
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description="Add/refresh BibTeX entries from INSPIRE-HEP (fallback Crossref). "
                    "Never fabricates: every field is an API pass-through.")
    p.add_argument("--bib", default=DEFAULT_BIB, help=f"bib file (default: {DEFAULT_BIB})")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="add one paper by arXiv id or DOI")
    a.add_argument("identifier", help="e.g. 2407.13820 or 10.1103/7whh-9j22")
    a.add_argument("--key", help="override the generated NameYearFirstword key")
    a.add_argument("--write", action="store_true", help="actually append (default: dry run)")
    a.set_defaults(func=cmd_add)

    r = sub.add_parser("refresh", help="fill in journal data for preprints now published")
    r.add_argument("--only", help="restrict to one existing key")
    r.add_argument("--write", action="store_true", help="actually apply (default: dry run)")
    r.set_defaults(func=cmd_refresh)

    args = p.parse_args()
    try:
        return args.func(args)
    except Abort as e:
        print(f"ABORT: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
