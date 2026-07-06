#include "logforge/parse_number.hpp"

#include <cctype>
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

// A numeric token is built from digits, a single decimal point and an optional
// leading minus sign. We screen the trimmed text for those characters before
// converting so that stray, non-numeric text is rejected.
bool looksNumeric(const std::string& s) {
	for (char c : s) {
		if (std::isdigit(static_cast<unsigned char>(c))) {
			continue;
		}
		if (c == '.' || c == '-') {
			continue;
		}
		return false;
	}
	return true;
}

}  // namespace

std::optional<double> parseDouble(const std::string& text) {
	const std::string trimmed = trim(text);
	if (trimmed.empty()) {
		return std::nullopt;
	}
	if (!looksNumeric(trimmed)) {
		return std::nullopt;
	}
	const char* begin = trimmed.c_str();
	char* end = nullptr;
	const double value = std::strtod(begin, &end);
	// The whole trimmed string must be consumed for it to be a valid number.
	if (end != begin + trimmed.size()) {
		return std::nullopt;
	}
	return value;
}

}  // namespace logforge
