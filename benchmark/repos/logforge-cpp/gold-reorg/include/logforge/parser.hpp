#pragma once

#include <optional>
#include <string>
#include <vector>

namespace logforge {

// A Record is the decoded list of fields parsed from one input line.
using Record = std::vector<std::string>;

// parseLine splits one CSV line into fields and decodes each one, returning the
// finished record. A comma only separates fields when it is outside a
// double-quoted field, so a quoted field may itself contain commas. A field
// wrapped in double quotes has the surrounding quotes removed and every doubled
// quote ("") inside it collapsed to a single quote.
Record parseLine(const std::string& line);

// parseDouble converts a numeric text field to a double. It accepts an optional
// leading sign, a decimal point, and a scientific exponent (e/E with an optional
// sign). Surrounding spaces are ignored. It returns no value when the whole
// trimmed string is not a single valid decimal number. Only ordinary decimal
// numbers are accepted: hexadecimal floats and the words for infinity and
// not-a-number are not readings, and a reading must be finite.
std::optional<double> parseDouble(const std::string& text);

}  // namespace logforge
