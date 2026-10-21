#!/usr/bin/env python3
"""Guard the repository's own documentation — run by CI and by hand.

Checks, in this order:

  1. `SKILL.md` frontmatter: starts at byte 0, has `name` and `description`, and the
     description stays under 60 characters (the skill index truncates at 57).
  2. every file the docs POINT AT exists (`references/*.md`, `scripts/*.py`,
     `templates/*.py`, `examples/*`, and every relative Markdown link).
  3. every Python file compiles.

No third-party dependency: this must run on a bare runner.

    python3 tools/check_docs.py
"""
from __future__ import annotations

import pathlib
import py_compile
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ["SKILL.md", "README.md", "THIRD-PARTY.md"] + [
    str(p.relative_to(ROOT)) for p in sorted((ROOT / "references").glob("*.md"))
] + [str(p.relative_to(ROOT)) for p in sorted((ROOT / "examples").glob("*.md"))]

# Only paths that could be files OF THIS REPO: a known extension, and never a CDN path
# (`https://cdn…/three@0.128.0/examples/js/loaders/STLLoader.js` is not a repo file).
PATH_PATTERN = re.compile(
    r"(?<![\w/.:\-])((?:references|scripts|templates|examples|tools)/[A-Za-z0-9_.\-]+\.(?:md|py|sh|ya?ml|json))"
)
LINK_PATTERN = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")

problems: list[str] = []
checked_links = 0


def check_frontmatter() -> None:
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    if not text.startswith("---"):
        problems.append("SKILL.md: does not start with '---' at byte 0")
        return
    end = text.find("\n---", 3)
    if end == -1:
        problems.append("SKILL.md: frontmatter not closed")
        return
    block = text[3:end]
    for field in ("name:", "description:"):
        if field not in block:
            problems.append(f"SKILL.md: frontmatter missing '{field[:-1]}'")
    match = re.search(r'description:\s*"?(.*?)"?\s*$', block, re.M)
    if match:
        desc = match.group(1).strip()
        if len(desc) > 60:
            problems.append(f"SKILL.md: description is {len(desc)} chars (max 60): {desc!r}")
        if not desc.endswith("."):
            problems.append(f"SKILL.md: description must end with a period: {desc!r}")


def check_paths(doc: str, text: str) -> None:
    for target in sorted(set(PATH_PATTERN.findall(text))):
        if not (ROOT / target).exists():
            problems.append(f"{doc}: points at a missing file: {target}")


def check_links(doc: str, text: str) -> None:
    global checked_links
    for target in LINK_PATTERN.findall(text):
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        path = target.split("#")[0]
        if not path:
            continue
        checked_links += 1
        resolved = (ROOT / doc).parent / path
        if not resolved.exists():
            problems.append(f"{doc}: dead relative link: {target}")


def check_python() -> int:
    count = 0
    for path in sorted(ROOT.rglob("*.py")):
        if ".venv" in path.parts or ".git" in path.parts:
            continue
        count += 1
        try:
            py_compile.compile(str(path), cfile=tempfile.mktemp(), doraise=True)
        except py_compile.PyCompileError as exc:
            problems.append(f"{path.relative_to(ROOT)}: does not compile: {exc.msg}")
    return count


def main() -> int:
    check_frontmatter()
    for doc in DOCS:
        path = ROOT / doc
        if not path.exists():
            problems.append(f"{doc}: missing (listed in the docs)")
            continue
        text = path.read_text(encoding="utf-8")
        check_paths(doc, text)
        check_links(doc, text)
    py_files = check_python()

    if problems:
        print(f"{len(problems)} problem(s):")
        for problem in problems:
            print(f"  ✗ {problem}")
        return 1
    print(f"OK — {len(DOCS)} document(s), {checked_links} relative link(s), {py_files} Python file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
