#include "logforge/window.hpp"

#include "logforge/column.hpp"
#include "logforge/rolling.hpp"

namespace logforge {

std::vector<double> windowMeans(const std::vector<Record>& records, std::size_t index,
                                std::size_t window) {
	const std::vector<double> values = numericColumn(records, index);
	return rollingMean(values, window);
}

}  // namespace logforge
