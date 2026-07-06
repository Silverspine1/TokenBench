from tokenbench.scoring.parsing import parse_test_output


def test_pytest_structured_passed_and_failed():
    out = "===== 11 passed, 1 failed in 0.35s ====="
    r = parse_test_output("pytest -q tests/", passed=False, stdout_text=out)
    assert r["framework"] == "pytest"
    assert r["parse_confidence"] == "structured"
    assert r["tests_total"] == 12
    assert r["tests_passed"] == 11
    assert r["tests_failed"] == 1
    assert r["tests_skipped"] == 0
    assert r["command_passed"] is False


def test_pytest_structured_with_skips():
    out = "==== 3 passed, 2 skipped in 0.1s ===="
    r = parse_test_output("pytest", passed=True, stdout_text=out)
    assert r["tests_total"] == 5
    assert r["tests_passed"] == 3
    assert r["tests_skipped"] == 2
    assert r["parse_confidence"] == "structured"


def test_pytest_all_passed():
    out = "==== 13 passed in 0.35s ===="
    r = parse_test_output("pytest -q", passed=True, stdout_text=out)
    assert r["tests_total"] == 13
    assert r["tests_passed"] == 13
    assert r["tests_failed"] == 0


def test_pytest_errors_count_as_failed():
    out = "==== 1 passed, 2 errors in 0.2s ===="
    r = parse_test_output("pytest", passed=False, stdout_text=out)
    assert r["tests_failed"] == 2
    assert r["tests_passed"] == 1


def test_generic_fallback_when_no_summary():
    r = parse_test_output("npm test", passed=False, stdout_text="random noise")
    assert r["framework"] == "generic"
    assert r["parse_confidence"] == "command_level"
    assert r["tests_total"] == 1
    assert r["tests_passed"] == 0
    assert r["tests_failed"] == 1


def test_node_assert_script_falls_back_to_command_level():
    # Plain node assert script: passes, no framework summary -> command level.
    r = parse_test_output("node test_export.js", passed=True, stdout_text="hidden OK")
    assert r["framework"] == "generic"
    assert r["parse_confidence"] == "command_level"
    assert r["tests_passed"] == 1


def test_node_test_tap_summary():
    out = "# tests 5\n# pass 4\n# fail 1\n# skipped 0\n"
    r = parse_test_output("node --test", passed=False, stdout_text=out)
    assert r["framework"] == "node"
    assert r["parse_confidence"] == "structured"
    assert r["tests_total"] == 5
    assert r["tests_passed"] == 4
    assert r["tests_failed"] == 1


def test_vitest_summary():
    out = " Tests  3 passed | 1 failed (4)\n"
    r = parse_test_output("npx vitest run", passed=False, stdout_text=out)
    assert r["framework"] == "vitest"
    assert r["parse_confidence"] == "structured"
    assert r["tests_passed"] == 3
    assert r["tests_failed"] == 1
    assert r["tests_total"] == 4
