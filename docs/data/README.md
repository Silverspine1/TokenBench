# Data dictionary: run_results_2026-10.csv

One row per valid run in the published results: 1,101 rows. Cost and token figures come from the Claude Code CLI output for each run. Quality and success come from the hidden-test scorer (`tokenbench/scoring`). Derived columns were computed from run transcripts; the scripts are not published (see [METHODOLOGY](../METHODOLOGY.md#reproducibility)).

| Column | Meaning |
|---|---|
| `config` | `baseline`; the five tools in the headline table (`graphify` = Graphify 0.9.80, `ponytail` = Ponytail 5.0.0, `caveman` = Caveman plugin build of 2026-09-07, `crgraph` = code-review-graph 2.3.6, `rtk` = rtk 0.42.4); and two earlier first-pass runs that are not in the headline table, `ponytail_4_9_0` and `graphify_0_8_44`. |
| `task_id` | Task in `benchmark/suites/bank55.json` |
| `run_id` | Run directory name (timestamp, repo, task, short id) |
| `success` | 1 if quality >= 80, hidden-test pass rate >= 0.9 and no forbidden path modified |
| `quality_score` | 0.85 x hidden-test pass rate + 0.10 x visible-test pass rate + 0.05 x artifact integrity (0-100) |
| `cost_usd` | `total_cost_usd` reported by the Claude Code CLI (list-price token cost, including sub-agents) |
| `total_tokens` | All-thread tokens including cache reads and writes where the CLI reports them; main-thread tokens otherwise. The CSV does not flag which. |
| `output_tokens`, `thinking_tokens` | Main-thread output tokens; thinking tokens are part of output |
| `subagent_tokens` | Tokens used by sub-agents |
| `used_subagent` | 1 if the run called the Agent/Task tool |
| `tool_calls` | Total tool calls |
| `graph_or_mcp_calls` | Calls to MCP tools (the code-review-graph server). Always 0 for Graphify, which is queried through Bash, so this column does not show Graphify use. |
| `agent_wall_seconds` | Agent wall-clock time |
| `timed_out` | 1 if the agent hit its time limit (0 for every row) |
| `cli_version` | Claude Code CLI version recorded for the run |

Runs per config:

| config | runs | tasks | runs per task |
|---|---|---|---|
| baseline | 331 | 55 | 4-14 |
| graphify | 110 | 55 | 2 |
| ponytail | 110 | 55 | 2 |
| caveman | 110 | 55 | 2 |
| crgraph | 110 | 55 | 2 |
| rtk | 110 | 55 | 2 |
| ponytail_4_9_0 | 110 | 55 | 2 |
| graphify_0_8_44 | 110 | 55 | 2 |

Baseline rows are the valid August 2026 runs on the 55 tasks (22-24 August). Tool configs have two valid runs per task (7-8 October 2026). Quarantined runs, the rule for extra valid runs and the other exclusions are described in [METHODOLOGY](../METHODOLOGY.md#runs-exclusions-and-re-runs).
