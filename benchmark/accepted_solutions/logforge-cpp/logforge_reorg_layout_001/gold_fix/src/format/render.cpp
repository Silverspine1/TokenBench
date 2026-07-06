#include "logforge/render.hpp"

#include "logforge/format.hpp"

namespace logforge {

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
