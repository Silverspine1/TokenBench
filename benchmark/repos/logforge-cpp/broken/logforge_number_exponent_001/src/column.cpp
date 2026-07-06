#include "logforge/column.hpp"

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
			// Treat a missing cell and a non-positive reading the same way: only
			// values above zero contribute to the column.
			if (*v > 0.0) {
				values.push_back(*v);
			}
		}
	}
	return values;
}

}  // namespace logforge
