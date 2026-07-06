// Hidden behavioural check for stage 2: incremental (one-line-at-a-time)
// processing that honours the chosen input shape.
//
// Compiled against the candidate's library sources and run as a standalone
// binary. It feeds an input stream and asserts that the running summary computed
// without materialising all rows matches the full in-memory result, that it
// honours the selected input shape (delimiter + quote), and that quoting still
// protects the delimiter on the incremental path. It only compiles when the
// candidate exposes an incremental summary surface, so the stage-2 baseline
// (in-memory only) fails to build here. Exits non-zero if any case fails.
#include <cmath>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#include "logforge/dialect.hpp"
#include "logforge/stats.hpp"
#include "logforge/stream.hpp"

static int failures = 0;

static void check(const std::string& name, bool ok) {
	if (ok) {
		std::cout << "ok - " << name << "\n";
	} else {
		std::cout << "not ok - " << name << "\n";
		++failures;
	}
}

static bool close(double a, double b) { return std::fabs(a - b) < 1e-9; }

int main() {
	// 1. Streaming a comma-separated input reproduces the full summary.
	{
		std::istringstream in("name,value\na,10\nb,20\nc,30\n");
		logforge::Summary s = logforge::streamSummary(in, 1, logforge::defaultDialect(),
		                                              /*skipHeader=*/true);
		check("streamed count over csv", s.count == 3);
		check("streamed sum over csv", close(s.sum, 60.0));
		check("streamed mean over csv", close(s.mean, 20.0));
		check("streamed min/max over csv", close(s.min, 10.0) && close(s.max, 30.0));
	}
	// 2. Streaming honours a chosen input shape (semicolon separated).
	{
		std::istringstream in("name;value\na;5\nb;15\n");
		logforge::Dialect d{';', '"'};
		logforge::Summary s = logforge::streamSummary(in, 1, d, /*skipHeader=*/true);
		check("streamed count over ssv", s.count == 2);
		check("streamed mean over ssv", close(s.mean, 10.0));
		check("streamed min/max over ssv", close(s.min, 5.0) && close(s.max, 15.0));
	}
	// 3. A named shape selects the same behaviour on the incremental path.
	{
		std::istringstream in("name;value\nx;100\n");
		logforge::Summary s = logforge::streamSummary(in, 1, logforge::dialectByName("ssv"),
		                                              /*skipHeader=*/true);
		check("streamed named ssv reads the column", s.count == 1 && close(s.sum, 100.0));
	}
	// 4. Quoting still protects the chosen delimiter on the incremental path, so
	// the numeric column is read from the correct position.
	{
		std::istringstream in("label;value\n\"a;b\";42\n");
		logforge::Dialect d{';', '"'};
		logforge::Summary s = logforge::streamSummary(in, 1, d, /*skipHeader=*/true);
		check("streamed quoted delimiter keeps column alignment",
		      s.count == 1 && close(s.sum, 42.0));
	}
	// 5. Non-numeric cells are skipped on the incremental path.
	{
		std::istringstream in("name,value\na,10\nb,oops\nc,30\n");
		logforge::Summary s = logforge::streamSummary(in, 1, logforge::defaultDialect(),
		                                              /*skipHeader=*/true);
		check("streamed skips non-numeric cells", s.count == 2 && close(s.sum, 40.0));
	}
	// 6. An empty stream yields a zero summary.
	{
		std::istringstream in("");
		logforge::Summary s = logforge::streamSummary(in, 0, logforge::defaultDialect(),
		                                              /*skipHeader=*/false);
		check("streamed empty input is zero", s.count == 0 && close(s.sum, 0.0));
	}

	if (failures > 0) {
		std::cout << "FAILED: " << failures << " check(s)\n";
		return 1;
	}
	std::cout << "PASSED\n";
	return 0;
}
