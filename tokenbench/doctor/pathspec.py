"""Coarse glob-prefix overlap helpers for path-policy checks.

These are intentionally simple. A pattern like ``benchmark/**`` is reduced to its
leading directory prefix (``benchmark``); two patterns "overlap" when one prefix
is a path-segment prefix of the other. This is sufficient to catch the policy
mistakes the task doctor guards against (scored vs forbidden vs ignored), without
pulling in a full glob engine.
"""

from __future__ import annotations


def prefix_of(pattern: str) -> str:
    """Reduce a glob pattern to its leading directory prefix (no wildcards)."""
    p = pattern.replace("\\", "/").strip()
    segs: list[str] = []
    for seg in p.split("/"):
        if not seg:
            continue
        if "*" in seg or "?" in seg or seg == "**":
            break
        segs.append(seg)
    return "/".join(segs)


def patterns_overlap(a: str, b: str) -> bool:
    """True when two glob patterns can match an overlapping set of paths."""
    pa, pb = prefix_of(a), prefix_of(b)
    # An empty prefix means "matches from the root" -> overlaps anything.
    if pa == "" or pb == "":
        return True
    sa, sb = pa.split("/"), pb.split("/")
    n = min(len(sa), len(sb))
    return sa[:n] == sb[:n]


def path_under(path: str, pattern: str) -> bool:
    """True when ``path`` falls under the directory prefix of ``pattern``."""
    pre = prefix_of(pattern)
    if pre == "":
        return True
    norm = path.replace("\\", "/").strip("/")
    segs, pre_segs = norm.split("/"), pre.split("/")
    return segs[: len(pre_segs)] == pre_segs


def command_path_tokens(command: str) -> list[str]:
    """Extract path-like tokens (those containing a ``/``) from a shell command."""
    tokens: list[str] = []
    for raw in command.replace("\\", "/").split():
        tok = raw.strip("\"'")
        if "/" in tok:
            tokens.append(tok)
    return tokens
