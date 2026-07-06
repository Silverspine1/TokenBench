#pragma once

#include <string>
#include <vector>

#include "logforge/dialect.hpp"
#include "logforge/record.hpp"

namespace logforge {

// splitRecordWith breaks one line into its raw field tokens under the given
// dialect. The dialect's delimiter only separates fields when it is outside a
// quoted field, so a quoted field may itself contain the delimiter. The returned
// tokens are raw: any surrounding quotes and doubled-quote escapes are left in
// place for decodeField to interpret.
std::vector<std::string> splitRecordWith(const std::string& line, const Dialect& dialect);

// parseLineWith splits a line under the given dialect and decodes every field,
// returning the finished record a caller can use directly.
Record parseLineWith(const std::string& line, const Dialect& dialect);

// splitRecord/parseLine are the historical entry points: they apply the default
// (comma) dialect, so existing callers behave exactly as before.
std::vector<std::string> splitRecord(const std::string& line);
Record parseLine(const std::string& line);

}  // namespace logforge
