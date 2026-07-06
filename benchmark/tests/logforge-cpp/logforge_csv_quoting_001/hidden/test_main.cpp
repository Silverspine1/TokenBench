// Hidden behavioural check for CSV quoted-field parsing.
//
// Compiled against the candidate's library sources and run as a standalone
// binary. It asserts the documented CSV contract: commas inside quoted fields do
// not split, doubled quotes decode to a single quote, surrounding quotes are
// stripped, empty and space-bearing fields are preserved. Exits non-zero if any
// case fails.
#include <iostream>
#include <string>
#include <vector>

#include "logforge/csv.hpp"
#include "logforge/field.hpp"

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
	// 1. A plain line splits on commas.
	check("plain line splits into fields", eq(logforge::parseLine("a,b,c"), {"a", "b", "c"}));

	// 2. A comma inside a quoted field does not split the field.
	check("quoted comma stays in one field",
	      eq(logforge::parseLine("\"Smith, John\",42"), {"Smith, John", "42"}));

	// 3. Doubled quotes inside a quoted field decode to a single quote.
	check("doubled quotes decode to one quote",
	      eq(logforge::parseLine("\"she said \"\"hi\"\"\",x"), {"she said \"hi\"", "x"}));

	// 4. Empty fields are preserved.
	check("empty middle field preserved", eq(logforge::parseLine("a,,c"), {"a", "", "c"}));

	// 5. An unquoted field keeps its surrounding spaces.
	check("unquoted spaces preserved", eq(logforge::parseLine("  x ,y"), {"  x ", "y"}));

	// 6. An empty quoted field decodes to an empty string.
	check("empty quoted field decodes to empty", eq(logforge::parseLine("\"\",z"), {"", "z"}));

	// 7. A field that is only special characters, quoted, is a single field.
	check("fully quoted special chars are one field",
	      eq(logforge::parseLine("\"a,b,c\""), {"a,b,c"}));

	// 8. decodeField collapses doubled quotes on its own.
	check("decodeField collapses doubled quotes",
	      logforge::decodeField("\"he said \"\"x\"\"\"") == "he said \"x\"");

	// 9. decodeField leaves an unquoted token untouched.
	check("decodeField passes through unquoted token",
	      logforge::decodeField("plain") == "plain");

	// 10. A quote that is not the first character of a field is an ordinary
	// character: ab"c"d is literal text and does not start a quoted field.
	check("mid-field quote is literal",
	      eq(logforge::parseLine("ab\"c\"d,x"), {"ab\"c\"d", "x"}));

	// 11. Because that field is not quoted, a comma after it still splits.
	check("comma after mid-field quote still splits",
	      eq(logforge::parseLine("a\"b,c"), {"a\"b", "c"}));

	// 12. decodeField leaves a token whose quote is not at the front untouched.
	check("decodeField passes through mid-quote token",
	      logforge::decodeField("ab\"c\"d") == "ab\"c\"d");

	// 13. A field that opens with a quote, closes it, then has trailing text:
	// the quoted part is decoded and the trailing text is appended literally.
	check("quoted then trailing text", eq(logforge::parseLine("\"a\"b"), {"ab"}));

	if (failures > 0) {
		std::cout << "FAILED: " << failures << " check(s)\n";
		return 1;
	}
	std::cout << "PASSED\n";
	return 0;
}
