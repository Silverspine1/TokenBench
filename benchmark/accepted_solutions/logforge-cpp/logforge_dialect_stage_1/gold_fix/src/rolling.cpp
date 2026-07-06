#include "logforge/rolling.hpp"

namespace logforge {

std::vector<double> rollingMean(const std::vector<double>& values, std::size_t window) {
	std::vector<double> out;
	if (window == 0 || window > values.size()) {
		return out;
	}
	double sum = 0.0;
	for (std::size_t i = 0; i < window; ++i) {
		sum += values[i];
	}
	out.push_back(sum / static_cast<double>(window));
	for (std::size_t i = window; i < values.size(); ++i) {
		sum += values[i] - values[i - window];
		out.push_back(sum / static_cast<double>(window));
	}
	return out;
}

}  // namespace logforge
