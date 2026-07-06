#pragma once

#include <string>
#include <vector>

#include "logforge/record.hpp"

namespace logforge {

// numericColumn pulls one column out of a list of records and converts each
// present value to a double. A record that is too short to have the column is
// skipped. A cell that is not a valid number is skipped. The returned vector
// holds the numeric values in record order, so summary statistics and rolling
// windows see exactly the numbers a reader would read down that column.
std::vector<double> numericColumn(const std::vector<Record>& records, std::size_t index);

}  // namespace logforge
