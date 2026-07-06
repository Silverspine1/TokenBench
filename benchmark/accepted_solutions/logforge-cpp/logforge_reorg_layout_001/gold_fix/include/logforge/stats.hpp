#pragma once

#include <vector>

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

}  // namespace logforge
