// Visible smoke tests. Compiled and run by tests_visible/run_visible.py from the
// project root. These checks cover the basic wiring; they exit non-zero on the
// first failure. After the legacy import they talk to the consolidated surface
// in blob.hpp.
#include <iostream>
#include <vector>

#include "blob.hpp"

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
	{
		const lf::Rec r = lf::pl("a,b,c");
		check("plain line has three fields", r.size() == 3 && r[0] == "a" && r[2] == "c");
	}
	{
		const lf::Sm s = lf::sm({1.0, 2.0, 3.0});
		check("summary count", s.count == 3);
		check("summary mean", s.mean == 2.0);
		check("summary min/max", s.min == 1.0 && s.max == 3.0);
	}
	{
		const std::vector<double> m = lf::rm({1.0, 2.0, 3.0, 4.0}, 2);
		check("rolling mean length", m.size() == 3);
		check("rolling mean first", m.front() == 1.5);
	}
	check("format fixed", lf::ff(2.5, 2) == "2.50");

	if (failures > 0) {
		std::cout << "FAILED: " << failures << " check(s)\n";
		return 1;
	}
	std::cout << "all visible checks passed\n";
	return 0;
}
