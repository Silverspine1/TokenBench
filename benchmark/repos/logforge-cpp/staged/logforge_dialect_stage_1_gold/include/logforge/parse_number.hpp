#pragma once

#include <optional>
#include <string>

namespace logforge {

// parseDouble converts a numeric text field to a double. It accepts an optional
// leading sign, a decimal point, and a scientific exponent (e/E with an optional
// sign). Surrounding spaces are ignored. It returns no value when the whole
// trimmed string is not a single valid number. Only ordinary decimal numbers are
// accepted: a field built from anything outside the decimal-number characters --
// including hexadecimal floats and the words for infinity and not-a-number -- is
// not a reading and yields no value, and a reading must be finite.
std::optional<double> parseDouble(const std::string& text);

}  // namespace logforge
