#include "logforge/stream.hpp"

#include <string>

#include "logforge/csv.hpp"
#include "logforge/parse_number.hpp"
#include "logforge/record.hpp"

namespace logforge {

Summary streamSummary(std::istream& in, std::size_t column, const Dialect& dialect,
                      bool skipHeader) {
	Summary s;
	std::string line;
	bool header = skipHeader;
	bool seen = false;
	while (std::getline(in, line)) {
		if (header) {
			header = false;
			continue;
		}
		// Reuse the dialect-aware parser so the streaming path honours exactly the
		// same input shape as the in-memory path.
		const Record record = parseLineWith(line, dialect);
		if (column >= record.size()) {
			continue;
		}
		const auto value = parseDouble(record[column]);
		if (!value) {
			continue;
		}
		const double v = *value;
		if (!seen) {
			s.min = v;
			s.max = v;
			seen = true;
		}
		++s.count;
		s.sum += v;
		if (v < s.min) s.min = v;
		if (v > s.max) s.max = v;
	}
	if (seen) {
		s.mean = s.sum / static_cast<double>(s.count);
	}
	return s;
}

}  // namespace logforge
