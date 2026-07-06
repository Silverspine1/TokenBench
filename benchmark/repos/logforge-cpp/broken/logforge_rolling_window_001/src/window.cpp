#include "logforge/window.hpp"

#include "logforge/column.hpp"
#include "logforge/rolling.hpp"

namespace logforge {

std::vector<double> windowMeans(const std::vector<Record>& records, std::size_t index,
                                std::size_t window) {
	std::vector<double> values = numericColumn(records, index);
	// The first reading is a header carry-over from the column scan, so start the
	// moving average at the second reading.
	if (!values.empty()) {
		values.erase(values.begin());
	}
	return rollingMean(values, window);
}

}  // namespace logforge
