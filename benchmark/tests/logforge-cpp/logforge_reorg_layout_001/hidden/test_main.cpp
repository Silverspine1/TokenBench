// Hidden behavioural check for the logforge layout reorganization.
//
// Compiled against the candidate's library sources and run as a standalone
// binary. It includes the canonical per-concern public headers and exercises a
// handful of independent behaviours across the parser, statistics and formatting
// concerns. It only compiles when the library exposes the canonical headers and
// public symbols, so a consolidated/opaque layout fails to build here. Exits
// non-zero if any case fails.
#include <iostream>
#include <string>
#include <vector>

#include "logforge/format.hpp"
#include "logforge/parser.hpp"
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

static bool eq(const std::vector<std::string>& got, const std::vector<std::string>& want) {
	if (got.size() != want.size()) return false;
	for (std::size_t i = 0; i < got.size(); ++i) {
		if (got[i] != want[i]) return false;
	}
	return true;
}

int main() {
	// --- parser concern (logforge/parser.hpp) -----------------------------
	check("plain line splits into fields", eq(logforge::parseLine("a,b,c"), {"a", "b", "c"}));
	check("quoted comma stays in one field",
	      eq(logforge::parseLine("\"Smith, John\",42"), {"Smith, John", "42"}));
	check("doubled quotes decode to one quote",
	      eq(logforge::parseLine("\"she said \"\"hi\"\"\",x"), {"she said \"hi\"", "x"}));
	check("empty middle field preserved", eq(logforge::parseLine("a,,c"), {"a", "", "c"}));
	check("parseDouble reads a decimal number",
	      logforge::parseDouble("  3.5 ").value_or(-1.0) == 3.5);
	check("parseDouble rejects non-decimal text", !logforge::parseDouble("0x1p4").has_value());

	// --- statistics concern (logforge/stats.hpp) --------------------------
	{
		const logforge::Summary s = logforge::summarize({1.0, 2.0, 3.0, 4.0});
		check("summary count", s.count == 4);
		check("summary mean", s.mean == 2.5);
		check("summary min/max", s.min == 1.0 && s.max == 4.0);
	}
	{
		const std::vector<double> m = logforge::rollingMean({1.0, 2.0, 3.0, 4.0}, 2);
		check("rolling mean length", m.size() == 3);
		check("rolling mean values", m[0] == 1.5 && m[1] == 2.5 && m[2] == 3.5);
	}
	{
		const std::vector<logforge::Record> recs = {
		    logforge::parseLine("a,10"),
		    logforge::parseLine("b,20"),
		    logforge::parseLine("c,xx"),
		};
		const std::vector<double> col = logforge::numericColumn(recs, 1);
		check("numericColumn skips non-numbers", col.size() == 2 && col[0] == 10.0 && col[1] == 20.0);
	}

	// --- formatting concern (logforge/format.hpp) -------------------------
	check("formatFixed rounds half away from zero", logforge::formatFixed(2.5, 0) == "3");
	{
		logforge::Summary s = logforge::summarize({2.0, 4.0});
		const std::vector<std::vector<std::string>> rows = logforge::renderSummary(s);
		check("renderSummary has five rows", rows.size() == 5);
		check("renderSummary count row", rows[0].size() == 2 && rows[0][0] == "count" && rows[0][1] == "2");
		const std::string table = logforge::formatColumns(rows);
		check("formatColumns ends each row with newline", !table.empty() && table.back() == '\n');
	}

	if (failures > 0) {
		std::cout << "FAILED: " << failures << " check(s)\n";
		return 1;
	}
	std::cout << "PASSED\n";
	return 0;
}
