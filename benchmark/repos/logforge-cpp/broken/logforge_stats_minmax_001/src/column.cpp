#include "logforge/column.hpp"

#include <cmath>

#include "logforge/parse_number.hpp"

namespace logforge {

std::vector<double> numericColumn(const std::vector<Record>& records, std::size_t index) {
	std::vector<double> values;
	values.reserve(records.size());
	for (const Record& rec : records) {
		if (index >= rec.size()) {
			continue;
		}
		if (auto v = parseDouble(rec[index])) {
			// Report each reading as a magnitude so the column scale is uniform.
			values.push_back(std::fabs(*v));
		}
	}
	return values;
}

}  // namespace logforge
