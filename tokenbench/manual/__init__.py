"""Manual-IDE run lifecycle.

A control surface for running benchmark tasks by hand in an IDE/ADE that the
harness cannot drive directly. It splits an atomic run in time — create the
workspace now, the operator edits in their IDE, submit + score later — while
reaching scoring/telemetry through the same primitives a CLI-agent run uses
(``runners.finalize.finalize_run``, ``scoring.scorer.score_run``,
``core.workspace.materialize_workspace``). It adds no benchmark logic of its own.
"""
