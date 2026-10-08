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
Python/ML (`marketlab-ml`), PHP (`paygate-php-portal`), a Tauri/Rust desktop app (`vaultdesk-tauri`), a Node/TS SaaS app (`pulseboard-saas`), plus external real-world repos under `benchmark/external_repos/` (Python/Datasette, JS/undici, Go/mvm, C#/SharpTS). The published results use a 55-task bank (`benchmark/suites/bank55.json`: 43 tasks from the six in-house repos, 4 from `mvm`, 8 from `SharpTS`); the bank was cut from 73 tasks because tasks with fewer than about six to eight tool calls per run mostly measure run-to-run variance rather than the tool's effect. Datasette and undici are excluded from it (the model may have seen them in training). See [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md).

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
  - .NET SDK (`sharpts`) - `dotnet` on `PATH`
  - Node.js (`pulseboard-saas`, `undici`) — `node`/`npm` on `PATH`
  - Python 3 (`marketlab-ml`, `datasette`) — no extra toolchain beyond your interpreter

Task validation (`doctor-task`/`doctor-suite`) looks for these tools on `PATH`; tasks for a
toolchain you don't have installed will simply fail to build rather than corrupting other results.

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

## Published results (October 2026)

Claude Sonnet 4.6, 55 coding tasks, 2 runs per task, tool configs run on 7-8 October 2026. Cost is per 55-task pass; the
baseline is unmodified Claude Code from August 2026 (331 valid runs). A 10-task re-run in October found no detected difference from it (+0.4%, 95% CI -16% to +15%). The methodology lists the comparability checks. Cost per pass is the cost of one run through all 55 tasks, failed runs included; a negative cost change means cheaper than baseline. Intervals are
95% bootstrap intervals over tasks.

| Tool (version) | Cost per 55-task pass | Cost change vs baseline (95% CI) | Pass rate | Quality |
|---|---|---|---|---|
| Baseline | $26.44 | - | 72.2% | 89.2 |
| Graphify 0.9.80 | $19.01 | -28.1% (-35.1 to -21.1) | 73.6% | 89.5 |
| Ponytail 5.0.0 | $19.60 | -25.9% (-32.5 to -18.3) | 70.9% | 90.6 |
| Caveman (build of 2026-09-07) | $21.81 | -17.5% (-24.1 to -10.3) | 72.7% | 90.2 |
| code-review-graph 2.3.6 | $22.05 | -16.6% (-24.0 to -8.7) | 72.7% | 89.4 |
| rtk 0.42.4 | $26.76 | +1.2% (-4.3 to +7.7), no measurable effect | 72.7% | 90.6 |

Pass rate and quality do not differ from the baseline by more than noise for any tool; the quality penalty earlier versions of
Graphify and Ponytail showed is not visible with the versions above. Caveman, code-review-graph and rtk were not re-run on
their newest releases (see the methodology).

These figures differ from the tools' own headline claims because those claims measure one component in isolation (a command's
output, a graph query against reading the whole repo, output tokens), while a coding task is dozens of turns whose bill is
dominated by re-reading the accumulated context on every turn. A large saving in one piece can be cancelled by a single extra
turn.


## Reproducing the published results

The numbers at <https://tokenbench.app> come from the 55-task bank (`benchmark/suites/bank55.json`),
Claude Sonnet 4.6, 2 trials per task. The five tool configs ran in October 2026 with only the tool under test
active (`--effort high`, Claude Code 2.1.293). The baseline they are compared with is 331 runs of unmodified Claude
Code from August 2026 (`--agent claude_code_sonnet`). To run the isolated setup without any tool:

```bash
tokenbench run-suite benchmark/suites/bank55.json \
  --runner cli-agent \
  --agent claude_code_sonnet_iso \
  --condition my_run \
  --max-concurrency 8
```

(`run-suite` takes its trial count from the suite: `bank55.json` sets 2.)

`claude_code_sonnet_iso` runs Claude Code with project settings only (`--setting-sources project,local`)
and slash commands/skills disabled, which is intended to keep user-level plugins, skills, sub-agent definitions and MCP
servers out. Tool configs (`claude_code_sonnet_rtk`, `claude_code_sonnet_caveman`, `claude_code_sonnet_ponytail`, or `--graphify`)
add one tool each; edit the `<PATH-TO-...>` placeholders (plugin checkouts, and the absolute path to `rtk_settings.json`).
code-review-graph is not reproducible from this repository yet (the graph-build step and `--mcp-config` support are missing).
For the baseline use `--agent claude_code_sonnet`.

[`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) lists the exact conditions, tool versions, the baseline, why the bank is
55 tasks, which tools were and were not re-run on their latest release, the results with confidence intervals, and
the limitations. Per-run data for the runs behind the site is in
[`docs/data/run_results_2026-10.csv`](docs/data/run_results_2026-10.csv) (the scripts that computed its derived columns are not published yet).


## Where results go

Each run writes a timestamped directory under `runs/<timestamp>_<repo>_<task>_<id>/`
containing `score.json`, `telemetry.json`, and captured logs. Nothing under `runs/` is
tracked in git.

## Viewing results

```bash
tokenbench summarize runs/                     # ranked table across all score.json files
tokenbench aggregate runs/                      # per-condition aggregate + telemetry metrics
tokenbench compare runs/ --condition-a X --condition-b Y  # paired comparison of two conditions
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
