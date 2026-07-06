#pragma once

#include <string>
#include <vector>

#include "logforge/stats.hpp"

namespace logforge {

// formatFixed renders a value with exactly precision digits after the decimal
// point, rounding half away from zero, and never prints a "-0" for values that
// round to zero.
std::string formatFixed(double value, int precision);

// formatColumns lays out rows of cells into a left-aligned, space-padded table.
// Each column is as wide as its widest cell. Columns are separated by two spaces.
std::string formatColumns(const std::vector<std::vector<std::string>>& rows);

// renderSummary turns a statistics summary into the labelled rows the report
// prints: one {label, value} pair per figure (count, sum, mean, min, max). The
// count is rendered with no decimals; every other figure is rendered with two
// decimals, rounded half away from zero, and never as a negative zero.
std::vector<std::vector<std::string>> renderSummary(const Summary& summary);

}  // namespace logforge
