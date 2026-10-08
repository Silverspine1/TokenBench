# TokenBench methodology (October 2026 results)

How the published numbers were produced, what they show, and what they do not show. Per-run data: [`docs/data/run_results_2026-10.csv`](data/run_results_2026-10.csv). Column definitions: [`docs/data/README.md`](data/README.md).

## Summary

| | |
|---|---|
| Model | Claude Sonnet 4.6 (`claude-sonnet-4-6`), `--effort high` |
| Tasks | 55 coding tasks, [`benchmark/suites/bank55.json`](../benchmark/suites/bank55.json) |
| Tool runs | 7-8 October 2026. Two valid runs per task per tool, 110 runs per tool. Claude Code 2.1.293 (one exception, see Tool setup) |
| Baseline | 331 valid runs of unmodified Claude Code with default settings, 22-24 August 2026, Claude Code 2.1.239-2.1.241 (recorded per run), 4-14 runs per task |
| Web access | `WebSearch` and `WebFetch` disallowed in every run, baseline included |

* **Cost** is the `total_cost_usd` the Claude Code CLI reports for each run: token usage at list prices, including sub-agent spend. Graph build cost is excluded for Graphify and code-review-graph.
* **Quality** = 0.85 x hidden-test pass rate + 0.10 x visible-test pass rate + 0.05 x artifact integrity (`tokenbench/scoring/quality.py`). There is no AI judge. **Success** = quality >= 80, hidden-test pass rate >= 0.9 and no forbidden path modified (`tokenbench/scoring/scorer.py`).
* **Aggregation.** Per-task means first, then summed (cost) or averaged (success, quality) over the 55 tasks. Intervals are 95% paired bootstrap intervals over tasks (2,000 resamples) on the change versus baseline. A negative change is cheaper.

## Results

Cost per 55-task pass, failed runs included.

| Tool (version) | Cost per 55-task pass | Cost change vs baseline [95% CI] | Success | Quality |
|---|---|---|---|---|
| Baseline | $26.44 | - | 72.2% | 89.2 |
| Graphify 0.9.80 | $19.01 | -28.1% [-35.1, -21.1] | 73.6% | 89.5 |
| Ponytail 5.0.0 | $19.60 | -25.9% [-32.5, -18.3] | 70.9% | 90.6 |
| Caveman (plugin build of 2026-09-07) | $21.81 | -17.5% [-24.1, -10.3] | 72.7% | 90.2 |
| code-review-graph 2.3.6 | $22.05 | -16.6% [-24.0, -8.7] | 72.7% | 89.4 |
| rtk 0.42.4 | $26.76 | +1.2% [-4.3, +7.7] (not significant) | 72.7% | 90.6 |

Graphify and Ponytail are statistically tied, as are Caveman and code-review-graph. Savings of about 5% or less are inside the noise. Success and quality differ from baseline by no more than the sampling noise at two runs per task. No significance test was run on success or quality.

## Baseline and comparability

The baseline is the largest unmodified sample: 331 valid runs, about six per task, against two per task for each tool. Because it is averaged over more runs, it is the more precise comparator. It is every valid August run on the 55 tasks, with these exclusions:

* 33 August runs on those tasks were flagged invalid by the harness and are excluded.
* 2 valid runs on `bizflow_holds_stage_1` have no recorded cost and are excluded (333 valid runs, 331 used).
* The August runs on the 25 removed tasks are not used.

The baseline was run in August 2026 on Claude Code 2.1.239-2.1.241 with default settings. The tool runs were run in October on Claude Code 2.1.293 with the isolated settings described under Isolation.

A 10-task check found no sign of a difference between the two, but it is small, so its intervals are wide (about plus or minus 15%) and cannot rule out a shift of that size. Runs with default settings in October, on 10 of the tasks, came out +0.4% against the August baseline on the same tasks (95% CI -16.2% to +14.9%). Isolated and default settings, both run in October on the same 10 tasks, came out -0.3% (95% CI -13.6% to +18.1%). Each check used two runs per task. The per-run rows for these checks are not part of this release.

A tighter, indirect check comes from the rtk arm. It ran all 55 tasks in the same October setup as the other tools and came out +1.2% against the August baseline (95% CI -4.3% to +7.7%). If the move from August default settings to the October isolated setup had shifted cost by 15% or more, rtk would be expected to show it unless rtk's own effect happened to cancel it. This is an inference from one tool arm, not a dedicated control.

## Runs, exclusions and re-runs

* Each tool has two valid runs per task, 110 runs per tool.
* **Quarantine.** A run is quarantined when the harness flags a fault, or when the process census finds leftover processes, a PATH or toolchain fault, a timeout, or a partial graph build. The affected task was run again. Before analysis, 54 run folders from the October sweep were quarantined. The slow-storage folder holds 41 runs across the tool arms: 7 with leftover processes, 3 timeouts, 23 without a run record, and 8 that completed but were quarantined with them. The ambient-process folder holds 3 Graphify 0.8.44 runs: one with a leftover process and two that completed. The PATH-fault folder holds 10 code-review-graph runs, where a PATH filter had removed pytest. Quarantined runs are not in the CSV.
* **First two valid runs.** Heal passes relabel re-runs, so a task can end up with more than two valid runs. The published arms keep the first two valid runs by start time. This dropped 2 valid Graphify 0.9.80 runs and 3 valid Ponytail 5.0.0 runs. One rtk attempt timed out with no cost and is not counted. The five dropped runs cost between 0.8 and 1.4 times their task's kept mean.
* **Outliers.** None were found in this release, so none were re-run.
* The baseline has no such rule: every valid run on the 55 tasks is used, as listed under Baseline and comparability.

## Task selection

The bank was cut from 73 tasks to 55 on 20 September 2026 (commit `06bf4bb`), after the earlier 73-task runs. The cut removed tasks with short runs. In a typical run those tasks used fewer than about six to eight tool calls. Such tasks mostly measure run-to-run variance rather than the tool's effect, and real coding sessions rarely look that short. Every task in the published bank has a median of at least 6 tool calls in its baseline runs; four of them are between 6 and 8.

This was a judgement made after seeing earlier results, not a rule fixed in advance. Results on the removed tasks are not published. Datasette and undici are excluded because the model may have seen them in training.

## Tool setup

| Arm | Version tested | Claude Code CLI (recorded per run) | How the tool is enabled |
|---|---|---|---|
| Baseline | unmodified Claude Code | 2.1.239-2.1.241 | default settings, `claude_code_sonnet` |
| Graphify | 0.9.80 (`pip install graphifyy==0.9.80`, [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify)) | 2.1.293 | AST graph built before the run; the agent queries it with `python -m graphify query`. Config `claude_code_sonnet_iso` plus `--graphify` |
| Ponytail | 5.0.0, tag `v5.0.0`, commit `b088b2df6e08d4306c6a3c3d575fe38c2d2d2989` ([DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail)) | 2.1.293 | Claude Code plugin via `--plugin-dir`, config `claude_code_sonnet_ponytail` (set the path) |
| Caveman | commit `15581d14007f...` ([JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman)), plugin build of 2026-09-07 | 2.1.293 | Claude Code plugin via `--plugin-dir`, config `claude_code_sonnet_caveman` (set the path) |
| rtk | 0.42.4 ([rtk-ai/rtk](https://github.com/rtk-ai/rtk)) | 2.1.293 | `rtk hook claude` as a `PreToolUse` Bash hook via `--settings`, config `claude_code_sonnet_rtk` with `rtk_settings.json` (set the absolute path) |
| code-review-graph | 2.3.6 (`pip install code-review-graph==2.3.6` in a clean virtualenv, [tirth8205/code-review-graph](https://github.com/tirth8205/code-review-graph)) | 2.1.293 | MCP server via `--mcp-config`, graph built before the run. The MCP config file and the graph-build step are not in this repository |

Earlier first-pass runs, in the CSV as `ponytail_4_9_0` (Ponytail 4.9.0, 2.1.293) and `graphify_0_8_44` (Graphify 0.8.44, 91 of 110 runs on Claude Code 2.1.287 and 19 on 2.1.293). They are not in the headline table.

Latest releases at the time:

| Tool | Version run | Latest at the time | Re-run on latest? |
|---|---|---|---|
| Graphify | 0.9.80 | 0.9.80 | yes |
| Ponytail | 5.0.0 | 5.0.0 (released 8 October 2026) | yes |
| Caveman | plugin build of 2026-09-07 | newer commits exist | no |
| code-review-graph | 2.3.6 | 2.3.9 | no |
| rtk | 0.42.4 | 0.51.0 | no |

Caveman, code-review-graph and rtk were not re-run on their newest releases. Their changelogs and diffs show bug fixes, wording clean-ups, additional filters for other commands and support for other coding agents. We did not find a change to how each works inside Claude Code. That is a judgement, not a measurement.

## Isolation

Tool runs use the isolated configuration, `benchmark/agents/claude_code_sonnet_iso.json`:

```
claude --print --output-format json --dangerously-skip-permissions \
  --disallowedTools WebSearch WebFetch \
  --model claude-sonnet-4-6 --effort high \
  --setting-sources project,local --disable-slash-commands
```

`--setting-sources project,local` keeps user-level plugins, hooks, custom sub-agent definitions and instruction files out. `--disable-slash-commands` disables skills and slash commands. The baseline runs the same command without the two isolation flags. Every run starts from a fresh copy of the task workspace. Isolation was checked on probe runs, not for every run. Claude Code's built-in sub-agents remain available.

## Measurement

* Cost, success and quality are as defined in the Summary.
* The derived columns (`used_subagent`, `thinking_tokens`, `output_tokens`, `subagent_tokens`, `tool_calls`, `graph_or_mcp_calls`) were computed from each run's transcript. The scripts that compute them are not published.
* `total_tokens` uses the all-thread count where the CLI reports it and the main-thread count otherwise. The CSV does not flag which.
* The per-task comparisons below sum per-task means over the 55 tasks, the same method as the cost headline.

## What the tools did

Change against baseline, per-task means summed over the 55 tasks. Sub-agent share is the share of runs that spawned a sub-agent (pooled over runs). Claude Code's built-in sub-agents are available and unconstrained in every arm, and whether to use one is the agent's own choice. The sub-agent columns therefore describe how each tool changed agent behaviour. They are a result of the tool, not a difference in how the benchmark was run. Sub-agent spend is included in cost because it is part of what a run costs.

| Arm | Runs spawning a sub-agent | Sub-agent tokens per pass | Thinking tokens | Output tokens | Tool calls |
|---|---|---|---|---|---|
| Baseline | 60% | 6.5 M | - | - | - |
| Graphify 0.9.80 | 0% | 0 | -15% | -2% | +20% |
| code-review-graph 2.3.6 | 0% | 0 | +12% | +14% | +42% |
| Caveman | 85% | 6.8 M | -28% | -20% | -4% |
| Ponytail 5.0.0 | 56% | 3.3 M | -28% | -18% | -7% |
| Ponytail 4.9.0 | 78% | 7.8 M | -30% | -19% | -6% |
| rtk | 81% | 7.6 M | -7% | -4% | -3% |

* **Graphify and code-review-graph:** these tools orient the agent up front, and it then chose no sub-agents: no run spawned one, against 60% of baseline runs, and sub-agent tokens fall to zero. Graphify's output tokens change little, and its thinking tokens fall by 15%. code-review-graph uses more tool calls and more thinking and output tokens than baseline.
* **Caveman and Ponytail:** thinking and output tokens fall against baseline. Their sub-agent use does not fall (Caveman) or falls only in Ponytail 5.0.0.
* **Ponytail 5.0.0 against 4.9.0:** sub-agent runs fall from 78% to 56%, and sub-agent tokens from 7.8 M to 3.3 M per pass. Thinking and output tokens per run change by +3% and +2%.
* **rtk:** the hook ran. The end-to-end effect is within noise.

Tool activation, from transcript scans (scripts not published): Graphify's graph was queried in 103 of 110 runs of the 0.8.44 arm and 104 of 112 run folders of the 0.9.80 arm. code-review-graph made at least one MCP call in every one of its 110 runs (mean 2.6 per run). Caveman and Ponytail instruction text appeared in every transcript scanned. The rtk hook ran in the transcripts scanned.

## Limitations

* Two valid runs per task per tool. Intervals resample tasks only. They do not capture run-to-run variance within a task.
* One model, one effort level, one machine.
* The baseline and the tool runs differ in time, Claude Code version and settings. The 10-task checks show no sign of a difference, but they are small and their intervals are about plus or minus 15%; the rtk arm (+1.2%, 95% CI -4.3% to +7.7%, 55 tasks) gives tighter indirect evidence.
* Caveman, code-review-graph and rtk were not re-run on their newest releases.
* Graph build cost is excluded. Cost is list price, not billed spend.
* The hidden tests, gold fixes and author notes (`private_notes.json` files and `task_author_notes` in the manifests) are in this repository. A model trained on this repository may have seen the answers. Treat the results as a snapshot for these tasks.
* The derived columns, transcript scans and the code-review-graph MCP config are not published (see Reproducibility).

## Reproducibility

Published here: the harness, the 55-task bank, the agent configs, the per-run CSV and this document. Not published: the run folders with transcripts, the scripts that compute the derived columns and the transcript scans, the quarantined run folders, the code-review-graph MCP config and graph-build step, and the per-run rows for the 10-task checks in Baseline and comparability. The CSV cannot be regenerated from this repository alone. To run the isolated and tool arms, see the README section Reproducing the published results.
