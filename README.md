# TokenBench

TokenBench is an agentic coding benchmark harness. It gives a coding agent (e.g. Claude
Code) a broken snapshot of a real or realistic repository plus a natural-language bug
report or feature request, lets the agent edit the workspace, then scores the result
against a hidden test suite the agent never sees.

Each task ships as:

- a **manifest** (`benchmark/manifests/**/*.json`) describing the prompt, the broken/gold
  snapshots, visible and hidden test commands, and scoring metadata
- a **broken snapshot** and a **gold snapshot** of the target repo
  (`benchmark/repos/<repo>/broken/<task>`, `benchmark/repos/<repo>/gold`)
- **hidden tests** the agent's patch is graded against (`benchmark/tests/**`)

Tasks span several language ecosystems: Go (`bizflow-go-sql`), C++ (`logforge-cpp`),
Python/ML (`marketlab-ml`), PHP (`paygate-php-portal`), a Tauri/Rust desktop app
(`vaultdesk-tauri`), a Node/TS SaaS app (`pulseboard-saas`), plus external real-world
repos under `benchmark/external_repos/` (Python/Datasette, JS/undici, Go/mvm, C#/SharpTS).

## Prerequisites

- Python 3.11+
- A coding agent CLI to benchmark. The shipped agent configs
  (`benchmark/agents/*.json`) target Claude Code (`npm install -g @anthropic-ai/claude-code`
  or equivalent, logged in with your own Anthropic account/API access).
- Per-repo-family toolchains, only needed for the repos you actually run:
  - Go (`bizflow-go-sql`, `mvm`) — a working `go` on `PATH`
  - C++ (`logforge-cpp`) — a C++17 compiler (`g++`/`clang++`) on `PATH`
  - PHP 8.3 (`paygate-php-portal`) — `php` on `PATH`
  - Rust + Tauri build deps (`vaultdesk-tauri`) — `cargo` on `PATH`, plus a MinGW/MSVC
    toolchain on Windows
  - Node.js (`pulseboard-saas`, `undici`) — `node`/`npm` on `PATH`
  - .NET SDK (`sharpts`) — `dotnet` on `PATH`
  - Python 3 (`marketlab-ml`, `datasette`) — no extra toolchain beyond your interpreter

Task validation (`doctor-task`/`doctor-suite`) looks for these tools on `PATH` (or via a
tool-specific env var like `CARGO`/`PHP`/`CXX`/`NODE`); tasks for a toolchain you don't
have installed will simply fail to build rather than corrupting other results.

## Install

```bash
pip install -e .
# optional: the local manual-IDE control surface (FastAPI UI)
pip install -e ".[ui]"
# dev extras (pytest, httpx) for running this repo's own test suite
pip install -e ".[dev]"
```

This installs the `tokenbench` CLI (entry point defined in `pyproject.toml`).

## Validate a task or suite

Before running anything, check that a task (or a whole suite) is internally consistent —
gold passes, broken fails the hidden tests, and the agent-facing prompt doesn't leak the
answer:

```bash
tokenbench doctor-task benchmark/manifests/marketlab-ml/marketlab_split_leakage_001.json
tokenbench doctor-suite benchmark/suites/v1_0_all_atomic.json
```

## Run a single task

```bash
tokenbench run benchmark/manifests/marketlab-ml/marketlab_split_leakage_001.json \
  --runner cli-agent \
  --agent claude_code_sonnet \
  --condition sonnet_base
```

`--agent` picks a config from `benchmark/agents/*.json` (which CLI/model/flags to invoke);
`--condition` is just a label recorded on the run for later grouping/comparison. Add
`--graphify` to build an AST knowledge-graph into the workspace first (a "repo map" tool
treatment condition).

## Run a whole suite

```bash
tokenbench run-suite benchmark/suites/v1_0_all_atomic.json \
  --agent claude_code_sonnet \
  --condition sonnet_base \
  --max-concurrency 4
```

Runs every task in the suite `required_trials` times each. `run-staged` runs a two-stage
task group (stage 2 starts from stage 1's own candidate output) — see
`benchmark/suites/*staged*.json`.

## Where results go

Each run writes a timestamped directory under `runs/<timestamp>_<repo>_<task>_<id>/`
containing `score.json`, `telemetry.json`, and captured logs. Nothing under `runs/` is
tracked in git.

## Viewing results

```bash
tokenbench summarize runs/                     # ranked table across all score.json files
tokenbench aggregate runs/                      # per-condition aggregate + telemetry metrics
tokenbench compare runs/ condition_a condition_b # paired comparison of two conditions
tokenbench build-db runs/ --db tokenbench.db    # ingest everything into a queryable SQLite db
```

`build-db` produces a `tokenbench.db` you can query directly with `sqlite3` (the
`run_results` view joins runs/telemetry/cost) if you want custom reporting beyond the
built-in commands.

## Manual / non-CLI-agent runs

If you want to benchmark an agent that isn't a scriptable CLI (e.g. a human using an IDE
plugin), use the manual flow: `tokenbench manual-start` materializes a workspace and
renders the prompt, you edit by hand, then `tokenbench manual-submit` freezes the
workspace, runs the hidden tests, and scores it. `tokenbench ui` starts a local web UI
(needs the `ui` extra) as a friendlier front end for the same flow. `bundle-export` /
`bundle-import` let you hand a task off to an external IDE as a zip and import the
resulting patch back in.

## Running this repo's own tests

```bash
pip install -e ".[dev]"
pytest -q
```

Note: the task-bank validity tests (`test_*_task_bank_valid.py`) actually build/run each
repo family's toolchain against its gold snapshot, so they'll skip or fail for language
toolchains you haven't installed — that's expected on a machine that isn't set up for
every language.
