"""
ignore.py — .onionignore and --exclude pattern matching
─────────────────────────────────────────────────────────
Supports glob-style patterns identical to .gitignore rules:
  *.pyc          match any .pyc file in any directory
  __pycache__/   match a directory named __pycache__
  __pycache__    match file or directory named __pycache__
  build/         match top-level build directory
  *.so           match any .so file

An .onionignore file in the root of the directory being compressed
is read automatically. Additional patterns can be supplied via
--exclude on the CLI.

Pattern rules (subset of gitignore):
  - Leading/trailing whitespace ignored
  - Lines starting with # are comments
  - A trailing / means directory-only match
  - * matches anything except /
  - ** matches anything including /
  - No leading / means match anywhere in the tree
  - Leading / means match only from the root
"""

import fnmatch
import os
from typing import List


IGNORE_FILENAME = ".onionignore"

# Sensible built-in defaults (can be overridden with --no-default-ignores)
DEFAULT_IGNORES = [
    "__pycache__/",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    ".git/",
    ".svn/",
    ".hg/",
    "*.so",
    "*.dylib",
    "*.dll",
    ".DS_Store",
    "Thumbs.db",
    "*.onion",        # don't compress existing archives
]


def _load_ignore_file(path: str) -> List[str]:
    """Read patterns from an .onionignore file. Returns [] if not found."""
    if not os.path.isfile(path):
        return []
    patterns = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n\r")
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                patterns.append(stripped)
    return patterns


def build_matcher(
    extra_patterns:      List[str],
    base_dir:            str  = "",
    use_default_ignores: bool = True,
) -> "IgnoreMatcher":
    """
    Build an IgnoreMatcher from:
      - built-in defaults (unless disabled)
      - .onionignore file in base_dir (if present)
      - extra_patterns from --exclude flags
    """
    patterns = []
    if use_default_ignores:
        patterns.extend(DEFAULT_IGNORES)
    if base_dir:
        ignore_file = os.path.join(base_dir, IGNORE_FILENAME)
        patterns.extend(_load_ignore_file(ignore_file))
    patterns.extend(extra_patterns)
    return IgnoreMatcher(patterns)


class IgnoreMatcher:
    """
    Given a list of glob patterns, decides whether a relative path
    (using forward slashes) should be ignored.
    """

    def __init__(self, patterns: List[str]):
        self._patterns = [p.strip() for p in patterns
                          if p.strip() and not p.strip().startswith("#")]

    def should_ignore(self, rel_path: str) -> bool:
        """
        Return True if *rel_path* (forward-slash separated, no leading /)
        matches any ignore pattern.
        """
        rel_path = rel_path.replace(os.sep, "/")
        parts    = rel_path.split("/")
        filename = parts[-1]

        for pattern in self._patterns:
            p = pattern

            # Directory-only pattern
            dir_only = p.endswith("/")
            if dir_only:
                p = p.rstrip("/")

            # Root-anchored pattern
            anchored = p.startswith("/")
            if anchored:
                p = p.lstrip("/")

            if dir_only:
                # Match any path component that is a directory segment
                for i, part in enumerate(parts[:-1]):   # exclude filename
                    if fnmatch.fnmatch(part, p):
                        return True
                    # Also try matching the partial path up to this component
                    partial = "/".join(parts[:i+1])
                    if fnmatch.fnmatch(partial, p):
                        return True
            elif anchored:
                # Must match from root
                if fnmatch.fnmatch(rel_path, p):
                    return True
            elif "/" in p:
                # Pattern contains slash — match against full relative path
                if fnmatch.fnmatch(rel_path, p):
                    return True
            else:
                # Simple pattern — match against filename or any path component
                if fnmatch.fnmatch(filename, p):
                    return True
                # Also check each directory component
                for part in parts[:-1]:
                    if fnmatch.fnmatch(part, p):
                        return True

        return False

    def active_patterns(self) -> List[str]:
        return list(self._patterns)
