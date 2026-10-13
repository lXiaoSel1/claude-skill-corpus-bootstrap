#!/usr/bin/env python3
"""Dependency-free reader for field-config.yaml (the subset stamp.py emits).

Shared by both instances (an identical copy lives in <field>-draft/pipeline/;
check_drift asserts the two copies match). Replaces the 2026-08 line parser,
which kept YAML quotes and inline comments inside values -- the reason
the mathematics instance's quoted abstract_end_markers never matched a single line.

Supported shape:
    key: value                 scalar; 'single' or "double" quotes removed
    key: value   # comment     inline comment stripped (outside quotes)
    key: [a, 'b c', "d"]       flow list
    key:                       block list follows (or empty value)
      - item   # comment
      - 'quoted item'
Keys: lowercase letters, digits, '_' and '-'. Anything else is ignored with a
warning collected in WARNINGS (never silently mis-parsed into a value).
"""
import re

WARNINGS = []
_KEY = re.compile(r"^([a-z][a-z0-9_\-]*):(?:\s+(.*)|\s*)$")
_ITEM = re.compile(r"^\s+-\s+(.*)$")


def _strip_comment(s):
    """Drop a trailing ' # comment' that is outside quotes."""
    q = None
    for i, ch in enumerate(s):
        if q:
            if ch == q:
                q = None
        elif ch in "'\"":
            q = ch
        elif ch == "#" and (i == 0 or s[i - 1] in " \t"):
            return s[:i].rstrip()
    return s.rstrip()


def _unquote(s):
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] == "'":
        return s[1:-1].replace("''", "'")          # YAML single quotes: literal
    if len(s) >= 2 and s[0] == s[-1] == '"':
        return s[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return s


def _split_flow(s):
    """[a, 'b, c', "d"] -> ['a', 'b, c', 'd']"""
    inner, out, cur, q = s.strip()[1:-1], [], "", None
    for ch in inner:
        if q:
            cur += ch
            if ch == q:
                q = None
        elif ch in "'\"":
            q = ch
            cur += ch
        elif ch == ",":
            out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    return [_unquote(x) for x in out if x.strip()]


def parse(path):
    """Return {key: str | list | None}. Missing file -> {}."""
    data, cur = {}, None
    try:
        with open(path, encoding="utf-8-sig") as fh:
            lines = fh.read().splitlines()
    except FileNotFoundError:
        return data
    except UnicodeDecodeError as e:
        raise SystemExit("%s is not UTF-8 (%s). Re-save it as UTF-8 -- "
                         "PowerShell 5.1 Set-Content writes the ANSI code "
                         "page by default." % (path, e))
    for n, raw in enumerate(lines, 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        m = _KEY.match(raw)
        if m:
            key, val = m.group(1), _strip_comment(m.group(2) or "")
            if val.startswith("[") and val.endswith("]"):
                data[key], cur = _split_flow(val), None
            elif val:
                data[key], cur = _unquote(val), None
            else:
                data[key], cur = None, key       # block list may follow
            continue
        m = _ITEM.match(raw)
        if m and cur:
            item = _unquote(_strip_comment(m.group(1)))
            if item:
                if not isinstance(data.get(cur), list):
                    data[cur] = []
                data[cur].append(item)
            continue
        WARNINGS.append("%s:%d not understood: %r" % (path, n, raw.strip()))
    return data


def as_list(v):
    if v is None:
        return []
    return list(v) if isinstance(v, list) else [v]


def as_str(v, default=""):
    if v is None:
        return default
    return " ".join(v) if isinstance(v, list) else v
