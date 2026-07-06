#include "logforge/parser.hpp"

#include <cctype>
#include <cmath>
#include <cstdlib>

namespace logforge {

namespace {

std::vector<std::string> splitRecord(const std::string& line) {
	std::vector<std::string> fields;
	std::string cur;
	bool inQuotes = false;
	// A double quote only opens a quoted section when it is the very first
	// character of a field. Anywhere else it is an ordinary character.
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

std::string decodeField(const std::string& raw) {
	if (raw.empty() || raw.front() != '"') {
		return raw;
	}
	std::string out;
	out.reserve(raw.size());
	std::size_t i = 1;  // skip the opening quote
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

Record parseLine(const std::string& line) {
	Record record;
	for (const std::string& raw : splitRecord(line)) {
		record.push_back(decodeField(raw));
	}
	return record;
}

std::optional<double> parseDouble(const std::string& text) {
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

}  // namespace logforge
