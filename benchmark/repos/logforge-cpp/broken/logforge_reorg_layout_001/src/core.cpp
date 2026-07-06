#include "blob.hpp"

#include <cctype>
#include <cmath>
#include <cstdio>
#include <cstdlib>

// Catch-all translation unit from the legacy import: the line parser, numeric
// field reader, summary statistics, rolling mean, column reader, fixed-point
// formatter, column layout and summary renderer all live here together under
// short internal names.
namespace lf {

namespace {

std::vector<std::string> splitLine(const std::string& line) {
	std::vector<std::string> fields;
	std::string cur;
	bool inQuotes = false;
	bool atFieldStart = true;
	for (std::size_t i = 0; i < line.size(); ++i) {
		const char c = line[i];
		if (inQuotes) {
			if (c == '"') {
				if (i + 1 < line.size() && line[i + 1] == '"') {
					cur.push_back('"');
					cur.push_back('"');
					++i;
				} else {
					inQuotes = false;
					cur.push_back('"');
				}
			} else {
				cur.push_back(c);
			}
		} else {
			if (c == ',') {
				fields.push_back(cur);
				cur.clear();
				atFieldStart = true;
			} else if (c == '"' && atFieldStart) {
				inQuotes = true;
				cur.push_back('"');
				atFieldStart = false;
			} else {
				cur.push_back(c);
				atFieldStart = false;
			}
		}
	}
	fields.push_back(cur);
	return fields;
}

std::string decode(const std::string& raw) {
	if (raw.empty() || raw.front() != '"') {
		return raw;
	}
	std::string out;
	out.reserve(raw.size());
	std::size_t i = 1;
	bool closed = false;
	for (; i < raw.size(); ++i) {
		if (raw[i] == '"') {
			if (i + 1 < raw.size() && raw[i + 1] == '"') {
				out.push_back('"');
				++i;
			} else {
				closed = true;
				++i;
				break;
			}
		} else {
			out.push_back(raw[i]);
		}
	}
	if (closed) {
		out.append(raw, i, std::string::npos);
	}
	return out;
}

std::string trim(const std::string& s) {
	std::size_t a = 0;
	std::size_t b = s.size();
	while (a < b && std::isspace(static_cast<unsigned char>(s[a]))) ++a;
	while (b > a && std::isspace(static_cast<unsigned char>(s[b - 1]))) --b;
	return s.substr(a, b - a);
}

bool isDecimalNumberText(const std::string& s) {
	for (const char c : s) {
		const bool ok = (c >= '0' && c <= '9') || c == '+' || c == '-' ||
		                c == '.' || c == 'e' || c == 'E';
		if (!ok) {
			return false;
		}
	}
	return true;
}

}  // namespace

Rec pl(const std::string& line) {
	Rec record;
	for (const std::string& raw : splitLine(line)) {
		record.push_back(decode(raw));
	}
	return record;
}

std::optional<double> pd(const std::string& text) {
	const std::string trimmed = trim(text);
	if (trimmed.empty()) {
		return std::nullopt;
	}
	if (!isDecimalNumberText(trimmed)) {
		return std::nullopt;
	}
	const char* begin = trimmed.c_str();
	char* end = nullptr;
	const double value = std::strtod(begin, &end);
	if (end != begin + trimmed.size()) {
		return std::nullopt;
	}
	if (!std::isfinite(value)) {
		return std::nullopt;
	}
	return value;
}

Sm sm(const std::vector<double>& values) {
	Sm s;
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

std::vector<double> nc(const std::vector<Rec>& records, std::size_t index) {
	std::vector<double> values;
	values.reserve(records.size());
	for (const Rec& rec : records) {
		if (index >= rec.size()) {
			continue;
		}
		if (auto v = pd(rec[index])) {
			values.push_back(*v);
		}
	}
	return values;
}

std::vector<double> rm(const std::vector<double>& values, std::size_t window) {
	std::vector<double> out;
	if (window == 0 || window > values.size()) {
		return out;
	}
	double sum = 0.0;
	for (std::size_t i = 0; i < window; ++i) {
		sum += values[i];
	}
	out.push_back(sum / static_cast<double>(window));
	for (std::size_t i = window; i < values.size(); ++i) {
		sum += values[i] - values[i - window];
		out.push_back(sum / static_cast<double>(window));
	}
	return out;
}

std::string ff(double value, int precision) {
	if (precision < 0) {
		precision = 0;
	}
	const double scale = std::pow(10.0, precision);
	double rounded = std::round(value * scale) / scale;
	if (rounded == 0.0) {
		rounded = 0.0;
	}
	char buf[64];
	std::snprintf(buf, sizeof(buf), "%.*f", precision, rounded);
	return std::string(buf);
}

std::string fc(const std::vector<std::vector<std::string>>& rows) {
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

std::vector<std::vector<std::string>> rs(const Sm& summary) {
	std::vector<std::vector<std::string>> rows;
	rows.push_back({"count", ff(static_cast<double>(summary.count), 0)});
	rows.push_back({"sum", ff(summary.sum, 2)});
	rows.push_back({"mean", ff(summary.mean, 2)});
	rows.push_back({"min", ff(summary.min, 2)});
	rows.push_back({"max", ff(summary.max, 2)});
	return rows;
}

}  // namespace lf
