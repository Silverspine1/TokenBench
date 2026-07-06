"""Hidden tests: multi-asset chronological split (M2).

"Sort by timestamp and split once" silently mis-allocates symbols of differing
density: a sparse, late symbol can lose its training rows and a dense symbol can
lose its share of test rows. The split must apply the test fraction per symbol,
keep each symbol's train rows strictly before its own test rows, and the
leakage check must actually flag a same-symbol violation.
"""

from marketlab.split import train_test_split_chrono_multi
from marketlab.validation import no_symbol_time_overlap

TEST_SIZE = 0.34


def _rows():
    # Dense symbol AAA (t1..t6) interleaved with sparse, late symbol BBB (t7,t8).
    return [
        {"symbol": "AAA", "t": 1, "close": 100.0},
        {"symbol": "AAA", "t": 2, "close": 101.0},
        {"symbol": "BBB", "t": 7, "close": 50.0},
        {"symbol": "AAA", "t": 3, "close": 102.0},
        {"symbol": "AAA", "t": 4, "close": 103.0},
        {"symbol": "AAA", "t": 5, "close": 104.0},
        {"symbol": "AAA", "t": 6, "close": 105.0},
        {"symbol": "BBB", "t": 8, "close": 49.0},
    ]


def _by_symbol(rows):
    out = {}
    for r in rows:
        out.setdefault(r["symbol"], []).append(r["t"])
    return out


def test_each_symbol_keeps_both_train_and_test():
    train, test = train_test_split_chrono_multi(_rows(), test_size=TEST_SIZE)
    train_syms = {r["symbol"] for r in train}
    test_syms = {r["symbol"] for r in test}
    all_syms = {r["symbol"] for r in _rows()}
    assert train_syms == all_syms, "a symbol lost all of its training rows"
    assert test_syms == all_syms, "a symbol lost all of its test rows"


def test_per_symbol_test_fraction_respected():
    _train, test = train_test_split_chrono_multi(_rows(), test_size=TEST_SIZE)
    test_counts = {}
    for r in test:
        test_counts[r["symbol"]] = test_counts.get(r["symbol"], 0) + 1
    # AAA has 6 rows -> round(6*0.34)=2; BBB has 2 -> max(1, round(0.68))=1.
    assert test_counts == {"AAA": 2, "BBB": 1}


def test_no_per_symbol_future_in_train():
    train, test = train_test_split_chrono_multi(_rows(), test_size=TEST_SIZE)
    max_train = {}
    for r in train:
        max_train[r["symbol"]] = max(max_train.get(r["symbol"], r["t"]), r["t"])
    min_test = {}
    for r in test:
        min_test[r["symbol"]] = min(min_test.get(r["symbol"], r["t"]), r["t"])
    for sym, lo in min_test.items():
        assert max_train[sym] < lo


def test_split_is_deterministic_and_order_preserving():
    a = train_test_split_chrono_multi(_rows(), test_size=TEST_SIZE)
    b = train_test_split_chrono_multi(_rows(), test_size=TEST_SIZE)
    assert a == b
    train, test = a
    assert len(train) + len(test) == len(_rows())


def test_validation_detects_a_same_symbol_violation():
    # AAA test row precedes an AAA train row -> must be reported as not clean.
    train = [{"symbol": "AAA", "t": 5}, {"symbol": "BBB", "t": 1}]
    test = [{"symbol": "AAA", "t": 2}, {"symbol": "BBB", "t": 9}]
    assert no_symbol_time_overlap(train, test) is False


def test_validation_accepts_a_clean_split():
    train, test = train_test_split_chrono_multi(_rows(), test_size=TEST_SIZE)
    assert no_symbol_time_overlap(train, test) is True


def test_train_and_test_are_order_preserving_subsequences():
    rows = _rows()
    train, test = train_test_split_chrono_multi(rows, test_size=TEST_SIZE)
    # Returned rows keep original relative order (stable subsequences of input).
    train_pos = [rows.index(r) for r in train]
    test_pos = [rows.index(r) for r in test]
    assert train_pos == sorted(train_pos)
    assert test_pos == sorted(test_pos)


def test_three_symbols_of_differing_density_each_keep_both_sides():
    rows = [
        {"symbol": "AAA", "t": 1, "close": 1.0},
        {"symbol": "AAA", "t": 2, "close": 1.0},
        {"symbol": "AAA", "t": 3, "close": 1.0},
        {"symbol": "AAA", "t": 4, "close": 1.0},
        {"symbol": "BBB", "t": 5, "close": 1.0},
        {"symbol": "BBB", "t": 6, "close": 1.0},
        {"symbol": "CCC", "t": 9, "close": 1.0},
        {"symbol": "CCC", "t": 10, "close": 1.0},
    ]
    train, test = train_test_split_chrono_multi(rows, test_size=0.5)
    all_syms = {"AAA", "BBB", "CCC"}
    assert {r["symbol"] for r in train} == all_syms
    assert {r["symbol"] for r in test} == all_syms
    assert no_symbol_time_overlap(train, test) is True


def test_every_symbol_keeps_at_least_one_test_row_even_when_sparse():
    # Sparse BBB (2 rows) must still contribute a test row (n_test >= 1).
    rows = _rows()
    _train, test = train_test_split_chrono_multi(rows, test_size=0.1)
    test_counts = {}
    for r in test:
        test_counts[r["symbol"]] = test_counts.get(r["symbol"], 0) + 1
    assert test_counts.get("AAA", 0) >= 1
    assert test_counts.get("BBB", 0) >= 1


def test_single_symbol_cut_is_last_fraction_in_time():
    rows = [{"symbol": "AAA", "t": t, "close": float(t)} for t in range(1, 6)]
    train, test = train_test_split_chrono_multi(rows, test_size=0.4)
    # round(5*0.4)=2 -> last two times in test.
    assert [r["t"] for r in test] == [4, 5]
    assert [r["t"] for r in train] == [1, 2, 3]
