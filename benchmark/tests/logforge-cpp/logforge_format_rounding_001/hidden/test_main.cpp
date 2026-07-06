// Hidden behavioural check for fixed-point formatting and summary rendering.
//
// Compiled against the candidate's library sources and run as a standalone
// binary. It asserts that fixed formatting rounds (not truncates), never prints a
// negative zero, and that the summary rows carry two decimals for every figure.
// Exits non-zero if any case fails.
#include <iostream>
#include <string>
#include <vector>

#include "logforge/format.hpp"
#include "logforge/render.hpp"
#include "logforge/stats.hpp"

static int failures = 0;

static void check(const std::string& name, bool ok) {
	if (ok) {
		std::cout << "ok - " << name << "\n";
	} else {
		std::cout << "not ok - " << name << "\n";
		++failures;
	}
}

int main() {
	// --- formatFixed rounds half away from zero ---
	// 1. A value just over the half mark rounds up.
	check("rounds 2.345 to 2.35", logforge::formatFixed(2.345, 2) == "2.35");
	// 2. Rounding carries into the next place.
	check("rounds 0.6 to 1 at zero places", logforge::formatFixed(0.6, 0) == "1");
	// 3. A negative value rounds away from zero.
	check("rounds -2.5 to -3 at zero places", logforge::formatFixed(-2.5, 0) == "-3");
	// 4. A value already at the precision is unchanged.
	check("keeps 2.50", logforge::formatFixed(2.5, 2) == "2.50");
	// 5. A whole number keeps its trailing zeros.
	check("keeps 4.00", logforge::formatFixed(4.0, 2) == "4.00");

	// --- rounding carries across the decimal point ---
	// 5a. A value just under ten rounds up and carries into the units and tens.
	check("carries 9.999 to 10.00", logforge::formatFixed(9.999, 2) == "10.00");
	// 5b. The same carry happens for a negative value, keeping its sign.
	check("carries -9.999 to -10.00", logforge::formatFixed(-9.999, 2) == "-10.00");
	// 5c. A carry can ripple across several places.
	check("carries 99.999 to 100.00", logforge::formatFixed(99.999, 2) == "100.00");

	// --- formatFixed never prints a negative zero ---
	// 6. A tiny negative that rounds to zero prints a plain zero.
	check("no negative zero at 2 places", logforge::formatFixed(-0.001, 2) == "0.00");
	// 7. A small negative that rounds to zero prints a plain zero.
	check("no negative zero at 0 places", logforge::formatFixed(-0.4, 0) == "0");
	// 7a. A negative value that rounds to zero at two places is a plain zero.
	check("no negative zero from -0.004", logforge::formatFixed(-0.004, 2) == "0.00");

	// --- renderSummary keeps two decimals for every figure ---
	logforge::Summary s;
	s.count = 3;
	s.sum = 6.0;
	s.mean = 2.0;
	s.min = 1.234;
	s.max = 5.678;
	std::vector<std::vector<std::string>> rows = logforge::renderSummary(s);
	// 8. There are five labelled rows.
	check("summary has five rows", rows.size() == 5);
	// 9. The min row carries two decimals, rounded.
	check("min row is two decimals",
	      rows.size() == 5 && rows[3].size() == 2 && rows[3][0] == "min" && rows[3][1] == "1.23");
	// 10. The max row carries two decimals, rounded.
	check("max row is two decimals",
	      rows.size() == 5 && rows[4].size() == 2 && rows[4][0] == "max" && rows[4][1] == "5.68");
	// 11. The mean row carries two decimals.
	check("mean row is two decimals",
	      rows.size() == 5 && rows[2][0] == "mean" && rows[2][1] == "2.00");

	if (failures > 0) {
		std::cout << "FAILED: " << failures << " check(s)\n";
		return 1;
	}
	std::cout << "PASSED\n";
	return 0;
}
