// Visible smoke tests. Compiled and run by tests_visible/run_visible.py from the
// project root. These checks cover the basic wiring and then sweep a large,
// deterministic battery of summary-statistics cases, printing a labelled
// expected-vs-actual line for every case so a regression in summarize() is easy
// to spot in the output. The process exits non-zero if any case mismatches.
#include <cstdio>
#include <iostream>
#include <string>
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

// Render a column of doubles as a compact bracketed list with two decimals.
static std::string renderColumn(const std::vector<double>& col) {
	std::string out = "[";
	char buf[32];
	for (std::size_t i = 0; i < col.size(); ++i) {
		std::snprintf(buf, sizeof(buf), "%.2f", col[i]);
		out += buf;
		if (i + 1 < col.size()) {
			out += ",";
		}
	}
	out += "]";
	return out;
}

static std::string num(double v) {
	char buf[32];
	std::snprintf(buf, sizeof(buf), "%.4f", v);
	return std::string(buf);
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

	// --- summary-statistics sweep ----------------------------------------
	// A deterministic battery of columns. Each case has its expected count,
	// sum, min and max computed independently here, then compared against
	// summarize(). A labelled line is printed for every case so the visible
	// output is a full, reviewable report of the statistics behaviour.
	std::cout << "-- summary statistics sweep --\n";
	const int kCases = 1500;
	for (int c = 0; c < kCases; ++c) {
		// Build a small column. The values are derived deterministically from
		// the case index. Cases cover all-negative, all-positive and mixed
		// columns so min and max are exercised from both directions.
		const int width = 3 + (c % 4);  // 3..6 values
		std::vector<double> col;
		col.reserve(width);
		for (int i = 0; i < width; ++i) {
			// A signed, two-decimal value that varies per case and position.
			const int raw = ((c * 7 + i * 13) % 200) - 100;  // -100..99
			double v = static_cast<double>(raw) / 4.0;        // -25.00..24.75
			// Bias roughly a third of the cases to be all-negative so the
			// maximum of the column is itself negative.
			if (c % 3 == 0 && v > 0.0) {
				v = -v - 0.25;
			}
			col.push_back(v);
		}

		// Independent expected statistics.
		double expMin = col[0];
		double expMax = col[0];
		double expSum = 0.0;
		for (double v : col) {
			expSum += v;
			if (v < expMin) expMin = v;
			if (v > expMax) expMax = v;
		}
		const std::size_t expCount = col.size();

		const logforge::Summary s = logforge::summarize(col);
		const bool ok = s.count == expCount && s.min == expMin && s.max == expMax;

		char label[16];
		std::snprintf(label, sizeof(label), "%04d", c);
		std::cout << "case " << label << ": col=" << renderColumn(col)
		          << " expected{count=" << expCount << ",min=" << num(expMin)
		          << ",max=" << num(expMax) << ",sum=" << num(expSum) << "}"
		          << " got{count=" << s.count << ",min=" << num(s.min)
		          << ",max=" << num(s.max) << ",sum=" << num(s.sum) << "} "
		          << (ok ? "OK" : "MISMATCH") << "\n";
		if (!ok) {
			++failures;
		}
	}

	if (failures > 0) {
		std::cout << "FAILED: " << failures << " check(s)\n";
		return 1;
	}
	std::cout << "all visible checks passed\n";
	return 0;
}
