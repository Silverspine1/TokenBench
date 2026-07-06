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

}  // namespace logforge
