#pragma once

#include <vector>

#include "logforge/parser.hpp"

namespace logforge {

// Summary holds the descriptive statistics of a column of numbers.
struct Summary {
	std::size_t count = 0;
	double sum = 0.0;
	double mean = 0.0;
	double min = 0.0;
	double max = 0.0;
};

// summarize computes the count, sum, mean, min and max of values. For an empty
// input every field is zero.
Summary summarize(const std::vector<double>& values);

// numericColumn pulls one column out of a list of records and converts each
// present value to a double. A record too short to have the column is skipped,
// and a cell that is not a valid number is skipped. The values are returned in
// record order.
std::vector<double> numericColumn(const std::vector<Record>& records, std::size_t index);

// rollingMean returns the moving average of values over a window of the given
// size. The result has one entry per full window, i.e. values.size() - window + 1
// entries; result[i] is the mean of values[i .. i + window - 1]. An empty result
// is returned when window is zero or larger than the input.
std::vector<double> rollingMean(const std::vector<double>& values, std::size_t window);

}  // namespace logforge
