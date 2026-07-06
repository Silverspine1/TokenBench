from tokenbench.scoring.efficiency import efficiency_components, file_churn_score


def test_within_max_is_unpenalized():
    assert file_churn_score(1, expected_changed_files_max=3) == 100.0
    assert file_churn_score(3, expected_changed_files_max=3) == 100.0


def test_above_max_is_penalized_ten_per_file():
    assert file_churn_score(4, expected_changed_files_max=3) == 90.0
    assert file_churn_score(6, expected_changed_files_max=3) == 70.0
    assert file_churn_score(13, expected_changed_files_max=3) == 0.0


def test_missing_max_uses_generic_taper():
    # Falls back to 5 points per scored file.
    assert file_churn_score(2, expected_changed_files_max=None) == 90.0
    assert file_churn_score(0, expected_changed_files_max=None) == 100.0


def test_efficiency_components_threads_expected_max():
    within = efficiency_components(
        total_wall_time_seconds=0.0,
        allowed_runtime_seconds=100.0,
        total_log_bytes=0,
        log_budget_bytes=1000,
        changed_scored_files=3,
        dependency_download_events=0,
        expected_changed_files_max=3,
    )
    assert within["file_churn_score"] == 100.0

    over = efficiency_components(
        total_wall_time_seconds=0.0,
        allowed_runtime_seconds=100.0,
        total_log_bytes=0,
        log_budget_bytes=1000,
        changed_scored_files=5,
        dependency_download_events=0,
        expected_changed_files_max=3,
    )
    assert over["file_churn_score"] == 80.0
