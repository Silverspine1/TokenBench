#pragma once

#include <string>
#include <vector>

#include "logforge/stats.hpp"

namespace logforge {

// renderSummary turns a statistics summary into the labelled rows the report
// prints: one {label, value} pair per figure (count, sum, mean, min, max). The
// count is rendered with no decimals; every other figure is rendered with two
// decimals, rounded half away from zero, and never as a negative zero.
std::vector<std::vector<std::string>> renderSummary(const Summary& summary);

}  // namespace logforge
