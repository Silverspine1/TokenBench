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

}  // namespace

std::optional<double> parseDouble(const std::string& text) {
	const std::string trimmed = trim(text);
	if (trimmed.empty()) {
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
