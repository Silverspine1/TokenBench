// Hidden behavioural check for the moving-average window.
//
// Compiled against the candidate's library sources and run as a standalone
// binary. It asserts that the rolling mean covers every full window with the
// correct values, and that the column-aware front end reads the whole column.
// Exits non-zero if any case fails.
#include <cmath>
#include <iostream>
#include <string>
#include <vector>

#include "logforge/record.hpp"
#include "logforge/rolling.hpp"
#include "logforge/window.hpp"

static int failures = 0;

static void check(const std::string& name, bool ok) {
	if (ok) {
		std::cout << "ok - " << name << "\n";
	} else {
		std::cout << "not ok - " << name << "\n";
		++failures;
	}
}

static bool near(double a, double b) {
	return std::fabs(a - b) < 1e-9;
}

int main() {
	// --- rollingMean: one entry per full window, each value correct ---
	std::vector<double> v = {1.0, 2.0, 3.0, 4.0};
	std::vector<double> m = logforge::rollingMean(v, 2);
	// 1. The result has values.size() - window + 1 entries.
	check("rolling length is N-w+1", m.size() == 3);
	// 2. The first window mean is correct.
	check("rolling first value", m.size() >= 1 && near(m[0], 1.5));
	// 3. The middle window mean is correct.
	check("rolling middle value", m.size() >= 2 && near(m[1], 2.5));
	// 4. The last window mean is correct.
	check("rolling last value", m.size() >= 3 && near(m[2], 3.5));

	// 5. A window of 3 produces the right means.
	std::vector<double> m3 = logforge::rollingMean({2.0, 4.0, 6.0, 8.0, 10.0}, 3);
	check("window-3 length", m3.size() == 3);
	check("window-3 values",
	      m3.size() == 3 && near(m3[0], 4.0) && near(m3[1], 6.0) && near(m3[2], 8.0));

	// 6. A window equal to the size yields a single mean over all points.
	std::vector<double> mAll = logforge::rollingMean({1.0, 3.0}, 2);
	check("full-width window", mAll.size() == 1 && near(mAll[0], 2.0));

	// 7. A window of 1 is the identity.
	std::vector<double> m1 = logforge::rollingMean({5.0, 7.0, 9.0}, 1);
	check("window-1 identity",
	      m1.size() == 3 && near(m1[0], 5.0) && near(m1[1], 7.0) && near(m1[2], 9.0));

	// --- windowMeans: reads the whole numeric column, no point dropped ---
	std::vector<logforge::Record> recs = {
		{"x", "10"},
		{"x", "20"},
		{"x", "30"},
		{"x", "40"},
	};
	std::vector<double> w = logforge::windowMeans(recs, 1, 2);
	// 8. The column-aware result covers every full window over all four readings.
	check("windowMeans length covers whole column", w.size() == 3);
	// 9. The first window mean uses the very first reading.
	check("windowMeans first uses first reading", w.size() >= 1 && near(w[0], 15.0));
	// 10. The last window mean uses the very last reading.
	check("windowMeans last uses last reading", w.size() >= 3 && near(w[2], 35.0));

	// 11. A column with non-numeric rows interleaved among the numbers: the
	// moving average runs over the numeric readings in order, as if the
	// non-numeric rows were not there. Numeric column is 10, 20, 30, so the
	// window-2 means are 15 and 25.
	std::vector<logforge::Record> mixed = {
		{"x", "10"},
		{"x", "skip"},
		{"x", "20"},
		{"x", ""},
		{"x", "30"},
	};
	std::vector<double> wm = logforge::windowMeans(mixed, 1, 2);
	check("windowMeans skips interleaved non-numeric rows",
	      wm.size() == 2 && near(wm[0], 15.0) && near(wm[1], 25.0));
	// 12. A window equal to the count of numeric readings yields a single mean
	// over all of them: 10, 20, 30 averages to 20.
	std::vector<double> wmAll = logforge::windowMeans(mixed, 1, 3);
	check("windowMeans full-width over numeric column",
	      wmAll.size() == 1 && near(wmAll[0], 20.0));

	// 13. A longer series exercises several slide steps in a row.
	std::vector<double> longSeries = logforge::rollingMean({4.0, 8.0, 6.0, 2.0, 10.0}, 2);
	check("rolling slide stays correct across the series",
	      longSeries.size() == 4 && near(longSeries[0], 6.0) && near(longSeries[1], 7.0) &&
	          near(longSeries[2], 4.0) && near(longSeries[3], 6.0));

	if (failures > 0) {
		std::cout << "FAILED: " << failures << " check(s)\n";
		return 1;
	}
	std::cout << "PASSED\n";
	return 0;
}
