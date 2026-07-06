#pragma once

#include <vector>

namespace logforge {

// rollingMean returns the moving average of values over a window of the given
// size. The result has one entry per full window, i.e. values.size() - window + 1
// entries; result[i] is the mean of values[i .. i + window - 1]. An empty result
// is returned when window is zero or larger than the input.
std::vector<double> rollingMean(const std::vector<double>& values, std::size_t window);

}  // namespace logforge
