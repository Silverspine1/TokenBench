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
			values.push_back(*v);
		}
	}
	return values;
}

}  // namespace logforge
