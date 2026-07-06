// Visible smoke tests. Compiled and run by tests_visible/run_visible.py from the
// project root. These checks cover the basic wiring; they exit non-zero on the
// first failure.
#include <iostream>
#include <vector>

#include "logforge/csv.hpp"
#include "logforge/format.hpp"
#include "logforge/rolling.hpp"
#include "logforge/stats.hpp"

static int failures = 0;

static void check(const char* name, bool ok) {
	if (ok) {
		std::cout << "ok - " << name << "\n";
	} else {
		std::cout << "not ok - " << name << "\n";
		++failures;
	}
}

int main() {
	// A plain, unquoted line splits into its fields.
	{
		const logforge::Record r = logforge::parseLine("a,b,c");
		check("plain line has three fields", r.size() == 3 && r[0] == "a" && r[2] == "c");
	}
	// Summary statistics over a small column.
	{
		const logforge::Summary s = logforge::summarize({1.0, 2.0, 3.0});
		check("summary count", s.count == 3);
		check("summary mean", s.mean == 2.0);
		check("summary min/max", s.min == 1.0 && s.max == 3.0);
	}
	// Rolling mean has one entry per full window.
	{
		const std::vector<double> m = logforge::rollingMean({1.0, 2.0, 3.0, 4.0}, 2);
		check("rolling mean length", m.size() == 3);
		check("rolling mean first", m.front() == 1.5);
	}
	// Fixed formatting.
	check("format fixed", logforge::formatFixed(2.5, 2) == "2.50");

	if (failures > 0) {
		std::cout << "FAILED: " << failures << " check(s)\n";
		return 1;
	}
	std::cout << "all visible checks passed\n";
	return 0;
}
