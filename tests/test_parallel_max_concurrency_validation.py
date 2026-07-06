"""--max-concurrency must be within 1..10; out-of-range fails loudly."""

import pytest
from typer.testing import CliRunner

from tokenbench.cli import app, validate_max_concurrency

runner = CliRunner()


def test_validate_accepts_in_range():
    for n in (1, 2, 5, 10):
        validate_max_concurrency(n)  # no raise


def test_validate_rejects_out_of_range():
    for n in (0, -1, 11, 100):
        with pytest.raises(ValueError):
            validate_max_concurrency(n)


def test_cli_rejects_too_high(tmp_path):
    # 11 is over the cap: the command exits nonzero before scheduling anything.
    result = runner.invoke(
        app,
        ["run-suite", "benchmark/suites/v0_5_smoke.json", "--max-concurrency", "11"],
    )
    assert result.exit_code != 0
    assert "max-concurrency" in result.output


def test_cli_rejects_zero(tmp_path):
    result = runner.invoke(
        app,
        ["run-suite", "benchmark/suites/v0_5_smoke.json", "--max-concurrency", "0"],
    )
    assert result.exit_code != 0
