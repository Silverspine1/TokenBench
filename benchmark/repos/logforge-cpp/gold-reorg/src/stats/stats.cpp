#include "logforge/stats.hpp"

namespace logforge {

Summary summarize(const std::vector<double>& values) {
	Summary s;
	if (values.empty()) {
		return s;
	}
	s.count = values.size();
	s.min = values[0];
	s.max = values[0];
	for (double v : values) {
		s.sum += v;
		if (v < s.min) s.min = v;
		if (v > s.max) s.max = v;
	}
	s.mean = s.sum / static_cast<double>(s.count);
	return s;
}

std::vector<double> numericColumn(const std::vector<Record>& records, std::size_t index) {
	std::vector<double> values;
	values.reserve(records.size());
	for (const Record& rec : records) {
		if (index >= rec.size()) {
			continue;
		}
		if (auto v = parseDouble(rec[index])) {
			values.push_back(*v);
		}
	}
	return values;
}

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
