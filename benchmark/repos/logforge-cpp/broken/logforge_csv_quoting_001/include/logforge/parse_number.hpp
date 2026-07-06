#pragma once

#include <optional>
#include <string>

namespace logforge {

// parseDouble converts a numeric text field to a double. It accepts an optional
// leading sign, a decimal point, and a scientific exponent (e/E with an optional
// sign). Surrounding spaces are ignored. It returns no value when the whole
// trimmed string is not a single valid number.
std::optional<double> parseDouble(const std::string& text);

}  // namespace logforge
