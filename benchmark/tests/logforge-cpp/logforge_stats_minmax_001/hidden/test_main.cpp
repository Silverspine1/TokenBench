// Hidden behavioural check for the statistics summary and column extraction.
//
// Compiled against the candidate's library sources and run as a standalone
// binary. It asserts that min and max are correct for all-negative and
// all-positive data and that a numeric column keeps each reading's sign. Exits
// non-zero if any case fails.
#include <cmath>
#include <iostream>
#include <string>
#include <vector>

#include "logforge/column.hpp"
#include "logforge/record.hpp"
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

static bool near(double a, double b) {
	return std::fabs(a - b) < 1e-9;
}

int main() {
	// --- summarize min/max for ordinary data ---
	logforge::Summary mixed = logforge::summarize({1.0, 2.0, 3.0});
	// 1. Positive data: min and max are the extremes of the data.
	check("positive min", near(mixed.min, 1.0));
	check("positive max", near(mixed.max, 3.0));

	// --- summarize for all-negative data ---
	logforge::Summary neg = logforge::summarize({-3.0, -2.0, -1.0});
	// 2. The maximum of all-negative data is the least negative value, not zero.
	check("all-negative max is -1", near(neg.max, -1.0));
	// 3. The minimum of all-negative data is the most negative value.
	check("all-negative min is -3", near(neg.min, -3.0));
	// 4. The sum of all-negative data is negative.
	check("all-negative sum", near(neg.sum, -6.0));

	// --- summarize for all-positive data well above zero ---
	logforge::Summary pos = logforge::summarize({5.0, 8.0, 12.0});
	// 5. The minimum of all-positive data is the smallest value, not zero.
	check("all-positive min is 5", near(pos.min, 5.0));
	check("all-positive max is 12", near(pos.max, 12.0));

	// 6. A single negative value is its own min and max.
	logforge::Summary one = logforge::summarize({-7.0});
	check("single negative min", near(one.min, -7.0));
	check("single negative max", near(one.max, -7.0));

	// 6a. A single positive value is its own min and max.
	logforge::Summary onePos = logforge::summarize({7.0});
	check("single positive min/max", near(onePos.min, 7.0) && near(onePos.max, 7.0));

	// 6b. When every value is identical, min and max are that value.
	logforge::Summary same = logforge::summarize({4.0, 4.0, 4.0});
	check("all-equal min/max", near(same.min, 4.0) && near(same.max, 4.0));

	// 6c. The mean is the true average, not an integer-divided quotient.
	logforge::Summary frac = logforge::summarize({1.0, 2.0});
	check("mean is exact average", near(frac.mean, 1.5));
	logforge::Summary frac3 = logforge::summarize({1.0, 2.0, 2.0});
	check("mean keeps its fraction", near(frac3.mean, 5.0 / 3.0));
	// 6d. The mean of all-negative data is negative and exact.
	check("all-negative mean exact", near(neg.mean, -2.0));

	// --- numericColumn keeps the sign of each reading ---
	std::vector<logforge::Record> recs = {{"-3"}, {"-1"}, {"-2"}};
	std::vector<double> col = logforge::numericColumn(recs, 0);
	// 7. Each negative reading keeps its sign.
	check("column keeps negative signs",
	      col.size() == 3 && near(col[0], -3.0) && near(col[1], -1.0) && near(col[2], -2.0));

	// 8. Summarizing a negative column gives a negative max, end to end.
	logforge::Summary colSummary = logforge::summarize(logforge::numericColumn(recs, 0));
	check("column-fed max is -1", near(colSummary.max, -1.0));
	check("column-fed min is -3", near(colSummary.min, -3.0));

	if (failures > 0) {
		std::cout << "FAILED: " << failures << " check(s)\n";
		return 1;
	}
	std::cout << "PASSED\n";
	return 0;
}
