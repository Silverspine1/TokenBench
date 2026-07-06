#include "logforge/parse_number.hpp"

#include <cctype>
#include <cmath>
#include <cstdlib>

namespace logforge {

namespace {

std::string trim(const std::string& s) {
	std::size_t a = 0;
	std::size_t b = s.size();
	while (a < b && std::isspace(static_cast<unsigned char>(s[a]))) ++a;
	while (b > a && std::isspace(static_cast<unsigned char>(s[b - 1]))) --b;
	return s.substr(a, b - a);
}

// A data number is written in ordinary decimal form: an optional sign, decimal
// digits, an optional decimal point, and an optional decimal exponent (e/E with
// an optional sign). It is composed only of those characters. The underlying
// string-to-double conversion is more permissive than that -- it would also
// accept hexadecimal floats and the words for infinity and not-a-number -- so a
// field that strays outside the decimal-number character set is not a data
// number even if the conversion would otherwise succeed.
bool isDecimalNumberText(const std::string& s) {
	for (const char c : s) {
		const bool ok = (c >= '0' && c <= '9') || c == '+' || c == '-' ||
		                c == '.' || c == 'e' || c == 'E';
		if (!ok) {
			return false;
		}
	}
	return true;
}

}  // namespace

std::optional<double> parseDouble(const std::string& text) {
	const std::string trimmed = trim(text);
	if (trimmed.empty()) {
		return std::nullopt;
	}
	// Only ordinary decimal numbers are valid readings. Hex floats, "inf" and
	// "nan" are not data, even though strtod would happily parse them.
	if (!isDecimalNumberText(trimmed)) {
		return std::nullopt;
	}
	const char* begin = trimmed.c_str();
	char* end = nullptr;
	const double value = std::strtod(begin, &end);
	// The whole trimmed string must be consumed for it to be a valid number.
	if (end != begin + trimmed.size()) {
		return std::nullopt;
	}
	// A reading that does not denote a finite quantity is not usable data.
	if (!std::isfinite(value)) {
		return std::nullopt;
	}
	return value;
}

}  // namespace logforge
