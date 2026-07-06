from marketlab.split import train_test_split_chrono


def test_chronological_no_leakage():
    rows = [{"id": i, "t": i} for i in range(10)]
    train, test = train_test_split_chrono(rows, 0.3)
    # Every training row must precede every test row in time.
    assert max(r["t"] for r in train) < min(r["t"] for r in test)


def test_sizes_and_order_preserved():
    rows = [{"id": i, "t": i} for i in range(10)]
    train, test = train_test_split_chrono(rows, 0.3)
    assert len(train) == 7
    assert len(test) == 3
    # No shuffling: concatenation reproduces the original ordering.
    assert train + test == rows
