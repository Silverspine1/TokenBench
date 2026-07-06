from tokenbench.scoring.efficiency import composite_efficiency, efficiency_components


def test_all_perfect():
    c = efficiency_components(
        total_wall_time_seconds=0.0,
        allowed_runtime_seconds=900,
        total_log_bytes=0,
        log_budget_bytes=250000,
        changed_scored_files=0,
        dependency_download_events=0,
    )
    assert c == {
        "wall_time_score": 100.0,
        "log_volume_score": 100.0,
        "file_churn_score": 100.0,
        "dependency_score": 100.0,
    }
    assert composite_efficiency(c) == 100.0


def test_wall_time_half():
    c = efficiency_components(450.0, 900, 0, 250000, 0, 0)
    assert c["wall_time_score"] == 50.0


def test_log_volume_half():
    c = efficiency_components(0.0, 900, 125000, 250000, 0, 0)
    assert c["log_volume_score"] == 50.0


def test_file_churn_scaling():
    c = efficiency_components(0.0, 900, 0, 250000, 3, 0)
    assert c["file_churn_score"] == 85.0  # 100 - 3*5


def test_file_churn_clamped():
    c = efficiency_components(0.0, 900, 0, 250000, 50, 0)
    assert c["file_churn_score"] == 0.0


def test_dependency_scaling():
    c = efficiency_components(0.0, 900, 0, 250000, 0, 2)
    assert c["dependency_score"] == 50.0  # 100 - 2*25


def test_composite_weights():
    c = {
        "wall_time_score": 80.0,
        "log_volume_score": 60.0,
        "file_churn_score": 100.0,
        "dependency_score": 0.0,
    }
    # 0.35*80 + 0.35*60 + 0.15*100 + 0.15*0 = 28 + 21 + 15 + 0 = 64
    assert composite_efficiency(c) == 64.0
