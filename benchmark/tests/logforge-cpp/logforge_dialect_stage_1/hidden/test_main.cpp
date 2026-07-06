// Hidden behavioural check for stage 1: selectable input shapes.
//
// Compiled against the candidate's library sources and run as a standalone
// binary. It asserts that a line can be parsed under a chosen input shape (a
// delimiter + quote character), that quoting still protects the chosen delimiter,
// that a named shape can be looked up, and that the historical comma entry points
// are unchanged. It only compiles when the candidate exposes a dialect-aware
// parse surface, so the stage-1 baseline (comma-only) fails to build here. Exits
// non-zero if any case fails.
#include <iostream>
#include <string>
#include <vector>

#include "logforge/csv.hpp"
#include "logforge/dialect.hpp"
#include "logforge/record.hpp"

static int failures = 0;

static void check(const std::string& name, bool ok) {
	if (ok) {
		std::cout << "ok - " << name << "\n";
	} else {
		std::cout << "not ok - " << name << "\n";
		++failures;
	}
}

static bool eq(const logforge::Record& got, const std::vector<std::string>& want) {
	if (got.size() != want.size()) return false;
	for (std::size_t i = 0; i < got.size(); ++i) {
		if (got[i] != want[i]) return false;
	}
	return true;
}

int main() {
	// 1. A semicolon-separated line splits on semicolons under that shape.
	{
		logforge::Dialect d{';', '"'};
		check("semicolon shape splits on semicolons",
		      eq(logforge::parseLineWith("a;b;c", d), {"a", "b", "c"}));
	}
	// 2. Under the semicolon shape a comma is ordinary data, not a separator.
	{
		logforge::Dialect d{';', '"'};
		check("comma is literal under semicolon shape",
		      eq(logforge::parseLineWith("a,b;c", d), {"a,b", "c"}));
	}
	// 3. Quoting still protects the chosen delimiter from splitting.
	{
		logforge::Dialect d{';', '"'};
		check("quoted delimiter stays in one field",
		      eq(logforge::parseLineWith("\"x;y\";z", d), {"x;y", "z"}));
	}
	// 4. Doubled quotes still decode inside a quoted field under a chosen shape.
	{
		logforge::Dialect d{';', '"'};
		check("doubled quotes decode under chosen shape",
		      eq(logforge::parseLineWith("\"she said \"\"hi\"\"\";z", d), {"she said \"hi\"", "z"}));
	}
	// 5. A named shape can be looked up: "ssv" selects the semicolon shape.
	{
		logforge::Dialect d = logforge::dialectByName("ssv");
		check("named ssv shape parses semicolons",
		      eq(logforge::parseLineWith("p;q", d), {"p", "q"}));
	}
	// 6. The default shape (and "csv") is comma separated.
	{
		logforge::Dialect d = logforge::dialectByName("csv");
		check("named csv shape parses commas",
		      eq(logforge::parseLineWith("p,q", d), {"p", "q"}));
	}
	// 7. The historical comma entry point is unchanged.
	check("default parseLine still splits on commas",
	      eq(logforge::parseLine("a,b,c"), {"a", "b", "c"}));
	// 8. The historical comma entry point still honours quoted commas.
	check("default parseLine honours quoted comma",
	      eq(logforge::parseLine("\"Smith, John\",42"), {"Smith, John", "42"}));

	if (failures > 0) {
		std::cout << "FAILED: " << failures << " check(s)\n";
		return 1;
	}
	std::cout << "PASSED\n";
	return 0;
}
