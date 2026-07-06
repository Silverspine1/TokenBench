from marketlab.split import train_test_split_chrono


def test_partition_is_complete():
    rows = [{"id": i, "t": i} for i in range(10)]
    train, test = train_test_split_chrono(rows, 0.3)
    ids = [r["id"] for r in train] + [r["id"] for r in test]
    # Every row appears exactly once across the two sets.
    assert len(ids) == 10
    assert sorted(ids) == list(range(10))
