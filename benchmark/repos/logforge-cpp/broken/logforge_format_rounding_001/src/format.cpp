#include "logforge/format.hpp"

#include <cmath>
#include <cstdio>
#include <vector>

namespace logforge {

std::string formatFixed(double value, int precision) {
	if (precision < 0) {
		precision = 0;
	}
	// Keep exactly the requested number of decimal places by scaling to whole
	// units, dropping the remaining fraction, and scaling back.
	const double scale = std::pow(10.0, precision);
	const double clipped = std::trunc(value * scale) / scale;
	char buf[64];
	std::snprintf(buf, sizeof(buf), "%.*f", precision, clipped);
	return std::string(buf);
}

std::string formatColumns(const std::vector<std::vector<std::string>>& rows) {
	std::vector<std::size_t> widths;
	for (const auto& row : rows) {
		for (std::size_t c = 0; c < row.size(); ++c) {
			if (c >= widths.size()) {
				widths.push_back(0);
			}
			if (row[c].size() > widths[c]) {
				widths[c] = row[c].size();
			}
		}
	}
	std::string out;
	for (const auto& row : rows) {
		for (std::size_t c = 0; c < row.size(); ++c) {
			out += row[c];
			if (c + 1 < row.size()) {
				out += std::string(widths[c] - row[c].size(), ' ');
				out += "  ";
			}
		}
		out += "\n";
	}
	return out;
}

}  // namespace logforge
