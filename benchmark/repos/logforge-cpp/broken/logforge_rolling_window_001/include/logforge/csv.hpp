#pragma once

#include <string>
#include <vector>

#include "logforge/record.hpp"

namespace logforge {

// splitRecord breaks one CSV line into its raw field tokens. A comma only
// separates fields when it is outside a double-quoted field, so a quoted field
// may itself contain commas. The returned tokens are raw: any surrounding quotes
// and doubled-quote escapes are left in place for decodeField to interpret.
std::vector<std::string> splitRecord(const std::string& line);

// parseLine splits a CSV line and decodes every field, returning the finished
// record a caller can use directly.
Record parseLine(const std::string& line);

}  // namespace logforge
