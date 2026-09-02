#!/usr/bin/env python3
"""Regenerate the file indexes for this repository.

Walks every course folder and writes a CSV listing each shared file together with
the raw URL that opens the file's contents directly. Those are the URLs that
read.csv() in R, pandas.read_csv() in Python, and anything else expecting a plain
file will accept; a github.com/.../blob/... address returns an HTML page instead
and will not parse.

Writes one index per course folder and one combined index at the repository root.

Run it with no arguments from anywhere in the repository:

    python tools/build_index.py

The repository and branch are read from the GitHub Actions environment when the
workflow runs it, and from the git remote otherwise.
"""

import argparse
import csv
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

RAW_HOST = "https://raw.githubusercontent.com"
INDEX_NAME = "index.csv"

# Repository machinery, not shared course material.
SKIP_DIRS = {".git", ".github", "tools", ".Rproj.user"}
SKIP_FILES = {
    INDEX_NAME,
    "README.md",
    "LICENSE",
    ".gitignore",
    ".gitattributes",
    ".gitkeep",
    ".DS_Store",
    "Thumbs.db",
}

COLUMNS = ["course", "file", "path", "type", "bytes", "updated", "url"]


def run(args, cwd=None):
    """Return stdout of a command, or an empty string if it fails."""
    try:
        out = subprocess.run(
            args, cwd=cwd, capture_output=True, text=True, check=True
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def repo_root():
    root = run(["git", "rev-parse", "--show-toplevel"])
    if root:
        return Path(root)
    # Fall back to the directory above this script.
    return Path(__file__).resolve().parent.parent


def repo_slug():
    """owner/name for the repository, however this script was started."""
    env = os.environ.get("GITHUB_REPOSITORY")
    if env:
        return env

    url = run(["git", "remote", "get-url", "origin"])
    if not url:
        return ""

    # Accept both https://github.com/owner/name(.git) and git@github.com:owner/name.git
    match = re.search(r"github\.com[:/]+([^/]+/[^/]+?)(?:\.git)?/?$", url)
    return match.group(1) if match else ""


def branch_name():
    env = os.environ.get("GITHUB_REF_NAME")
    if env:
        return env

    name = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    return name if name and name != "HEAD" else "main"


def last_updated(root, rel_path):
    """The commit date that last touched the file, which survives a fresh clone.

    A filesystem timestamp would be the checkout time on a CI runner and tell the
    reader nothing about the data.
    """
    stamp = run(
        ["git", "log", "-1", "--format=%cs", "--", str(rel_path)], cwd=str(root)
    )
    return stamp


def raw_url(slug, branch, rel_path):
    # Each path segment is encoded separately so the separators survive; a file
    # named "week 1 data.csv" would otherwise break the URL.
    encoded = "/".join(quote(part) for part in rel_path.parts)
    return f"{RAW_HOST}/{slug}/{branch}/{encoded}"


def collect(root, slug, branch):
    rows = []
    for course_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        if course_dir.name in SKIP_DIRS or course_dir.name.startswith("."):
            continue

        for path in sorted(course_dir.rglob("*")):
            if not path.is_file():
                continue
            if path.name in SKIP_FILES or path.name.startswith("."):
                continue
            if any(part in SKIP_DIRS for part in path.parts):
                continue

            rel = path.relative_to(root)
            rows.append(
                {
                    "course": course_dir.name,
                    "file": path.name,
                    "path": rel.as_posix(),
                    "type": path.suffix.lstrip(".").lower(),
                    "bytes": path.stat().st_size,
                    "updated": last_updated(root, rel),
                    "url": raw_url(slug, branch, rel),
                }
            )
    return rows


def write_csv(path, rows):
    """Write rows and report whether the file's contents actually changed.

    Returning False for an unchanged file keeps the workflow from committing a
    new version on every run.
    """
    previous = path.read_text(encoding="utf-8") if path.exists() else None

    lines = [",".join(COLUMNS)]
    for row in rows:
        buf = []
        for col in COLUMNS:
            value = str(row[col])
            if any(c in value for c in ',"\n'):
                value = '"' + value.replace('"', '""') + '"'
            buf.append(value)
        lines.append(",".join(buf))
    content = "\n".join(lines) + "\n"

    if content == previous:
        return False

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", help="owner/name, if not taken from the git remote")
    parser.add_argument("--branch", help="branch name, if not the current one")
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero if any index is out of date, writing nothing",
    )
    args = parser.parse_args()

    root = repo_root()
    slug = args.repo or repo_slug()
    branch = args.branch or branch_name()

    if not slug:
        sys.exit(
            "Could not work out the GitHub repository. Add an origin remote, or "
            "pass --repo owner/name."
        )

    rows = collect(root, slug, branch)

    targets = [(root / INDEX_NAME, rows)]
    for course in sorted({r["course"] for r in rows}):
        course_rows = [r for r in rows if r["course"] == course]
        targets.append((root / course / INDEX_NAME, course_rows))

    if args.check:
        stale = []
        for path, subset in targets:
            existing = path.read_text(encoding="utf-8") if path.exists() else None
            tmp = path.with_suffix(".csv.check")
            write_csv(tmp, subset)
            fresh = tmp.read_text(encoding="utf-8")
            tmp.unlink()
            if existing != fresh:
                stale.append(path.relative_to(root).as_posix())
        if stale:
            print("Out of date: " + ", ".join(stale))
            sys.exit(1)
        print(f"Indexes are current ({len(rows)} files).")
        return

    changed = [
        path.relative_to(root).as_posix()
        for path, subset in targets
        if write_csv(path, subset)
    ]

    courses = len({r["course"] for r in rows})
    print(f"{len(rows)} files across {courses} course folder(s).")
    print(f"Repository {slug}, branch {branch}.")
    if changed:
        print("Updated: " + ", ".join(changed))
    else:
        print("No index changes.")


if __name__ == "__main__":
    main()
