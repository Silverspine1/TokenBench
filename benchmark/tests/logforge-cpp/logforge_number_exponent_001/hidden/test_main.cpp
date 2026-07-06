// Hidden behavioural check for numeric parsing of a column.
//
// Compiled against the candidate's library sources and run as a standalone
// binary. It asserts that scientific-notation and signed numbers parse, and that
// a numeric column keeps negative and zero readings. Exits non-zero if any case
// fails.
#include <cmath>
#include <iostream>
#include <string>
#include <vector>

#include "logforge/column.hpp"
#include "logforge/parse_number.hpp"
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

static bool near(double a, double b) {
	return std::fabs(a - b) < 1e-9;
}

static bool parsedNear(const std::string& text, double want) {
	auto v = logforge::parseDouble(text);
	return v && near(*v, want);
}

int main() {
	// --- parseDouble accepts the full numeric grammar ---
	// 1. A plain integer parses.
	check("plain integer parses", parsedNear("42", 42.0));
	// 2. A decimal parses.
	check("decimal parses", parsedNear("3.5", 3.5));
	// 3. A negative number parses to a negative value.
	check("negative parses", parsedNear("-2.5", -2.5));
	// 4. Scientific notation with a positive exponent parses.
	check("scientific positive exponent parses", parsedNear("1.5e3", 1500.0));
	// 5. Scientific notation with a signed exponent parses.
	check("scientific signed exponent parses", parsedNear("-2E-2", -0.02));
	// 6. A leading plus sign parses.
	check("leading plus parses", parsedNear("+7", 7.0));
	// 7. Non-numeric text is still rejected.
	check("non-numeric rejected", !logforge::parseDouble("abc").has_value());
	// 7a. A leading-plus decimal also parses.
	check("leading plus decimal parses", parsedNear("+3.5", 3.5));
	// 7b. The word for infinity is not a data number, even though a raw
	// string-to-double conversion would accept it.
	check("inf rejected", !logforge::parseDouble("inf").has_value());
	// 7c. The word for not-a-number is not a data number.
	check("nan rejected", !logforge::parseDouble("nan").has_value());
	// 7d. A hexadecimal float is not a data number.
	check("hex float rejected", !logforge::parseDouble("0x1p4").has_value());
	// 7e. Case does not rescue the infinity/not-a-number words.
	check("INF rejected", !logforge::parseDouble("INF").has_value());
	check("NaN rejected", !logforge::parseDouble("NaN").has_value());

	// --- numericColumn keeps every numeric reading, including <= 0 ---
	std::vector<logforge::Record> recs = {
		{"a", "-3"},
		{"b", "0"},
		{"c", "5"},
		{"d", "1e2"},
	};
	std::vector<double> col = logforge::numericColumn(recs, 1);
	// 8. All four readings survive (negative, zero, positive, scientific).
	check("column keeps all numeric readings", col.size() == 4);
	// 9. The negative reading is kept with its sign.
	check("column keeps negative reading", col.size() >= 1 && near(col[0], -3.0));
	// 10. The zero reading is kept.
	check("column keeps zero reading", col.size() >= 2 && near(col[1], 0.0));
	// 11. The scientific reading is kept and decoded.
	check("column keeps scientific reading", col.size() >= 4 && near(col[3], 100.0));

	// 12. An all-negative column is not silently emptied.
	std::vector<logforge::Record> negs = {{"-1"}, {"-2"}, {"-3"}};
	check("all-negative column preserved", logforge::numericColumn(negs, 0).size() == 3);

	if (failures > 0) {
		std::cout << "FAILED: " << failures << " check(s)\n";
		return 1;
	}
	std::cout << "PASSED\n";
	return 0;
}
