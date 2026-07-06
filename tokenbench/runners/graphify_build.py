"""Build a graphify knowledge graph into a task workspace, before the agent runs.

AST-only: deterministic and free (zero LLM tokens), so building the graph never
contaminates the agent's measured token cost. The graph lands in
``<workspace>/graphify-out/graph.json``; ``graphify-out`` is a JUNK_DIRS name
(see ``core.paths``) so it never appears in the candidate diff or scoring.

This is the "graphify in every workspace" treatment condition: present the graph,
tell the agent to query it, and measure tokens/success vs the no-graph control.
"""

from __future__ import annotations

import sys
from pathlib import Path


def build_graph(workspace: Path) -> dict:
    """AST-extract ``workspace`` into ``workspace/graphify-out/graph.json``.

    Returns {nodes, edges} counts. Raises RuntimeError with an install hint if
    graphify is not importable in the harness environment. Pure structural
    extraction — no subagents, no API key, no token cost.
    """
    try:
        from graphify.build import build_from_json
        from graphify.cluster import cluster
        from graphify.export import to_json
        from graphify.extract import collect_files, extract
    except ImportError as e:  # pragma: no cover - environment guard
        raise RuntimeError(
            "graphify is not installed in the harness environment. "
            "Install it with: pip install graphifyy"
        ) from e

    workspace = Path(workspace)
    out_dir = workspace / "graphify-out"
    out_dir.mkdir(parents=True, exist_ok=True)

    files = collect_files(workspace)
    extraction = extract(files, cache_root=workspace)
    graph = build_from_json(extraction, root=str(workspace), directed=False)
    communities = cluster(graph)
    to_json(graph, communities, str(out_dir / "graph.json"))

    # The /graphify skill's fast-path reads this file to find the interpreter that
    # has graphify importable. The lightweight build above never runs the skill's
    # Step 1, so write it here: an agent that launches the skill (instead of running
    # `python -m graphify ...` straight from the prompt) then won't break on a
    # missing .graphify_python.
    (out_dir / ".graphify_python").write_text(sys.executable, encoding="utf-8")

    return {
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
    }
