#pragma once

#include <vector>

#include "logforge/record.hpp"

namespace logforge {

// windowMeans reads one numeric column out of the records and returns its moving
// average over a window of the given size. It is the column-aware front end over
// the rolling mean: result[i] is the mean of the i-th through (i+window-1)-th
// numeric values in the column, so the result has one entry per full window. An
// empty result is returned when the window is zero or wider than the column.
std::vector<double> windowMeans(const std::vector<Record>& records, std::size_t index,
                                std::size_t window);

}  // namespace logforge
