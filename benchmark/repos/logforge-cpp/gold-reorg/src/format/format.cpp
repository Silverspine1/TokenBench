#include "logforge/format.hpp"

#include <cmath>
#include <cstdio>

namespace logforge {

std::string formatFixed(double value, int precision) {
	if (precision < 0) {
		precision = 0;
	}
	// Round half away from zero at the requested precision.
	const double scale = std::pow(10.0, precision);
	double rounded = std::round(value * scale) / scale;
	if (rounded == 0.0) {
		// Collapse a negative zero to a plain zero.
		rounded = 0.0;
	}
	char buf[64];
	std::snprintf(buf, sizeof(buf), "%.*f", precision, rounded);
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

std::vector<std::vector<std::string>> renderSummary(const Summary& summary) {
	std::vector<std::vector<std::string>> rows;
	rows.push_back({"count", formatFixed(static_cast<double>(summary.count), 0)});
	rows.push_back({"sum", formatFixed(summary.sum, 2)});
	rows.push_back({"mean", formatFixed(summary.mean, 2)});
	rows.push_back({"min", formatFixed(summary.min, 2)});
	rows.push_back({"max", formatFixed(summary.max, 2)});
	return rows;
}

}  // namespace logforge
