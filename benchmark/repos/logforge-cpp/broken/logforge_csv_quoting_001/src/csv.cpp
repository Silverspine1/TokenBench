#include "logforge/csv.hpp"

#include "logforge/field.hpp"

namespace logforge {

std::vector<std::string> splitRecord(const std::string& line) {
	std::vector<std::string> fields;
	std::string cur;
	for (const char c : line) {
		if (c == ',') {
			fields.push_back(cur);
			cur.clear();
		} else {
			cur.push_back(c);
		}
	}
	fields.push_back(cur);
	return fields;
}

Record parseLine(const std::string& line) {
	Record record;
	for (const std::string& raw : splitRecord(line)) {
		record.push_back(decodeField(raw));
	}
	return record;
}

}  // namespace logforge
