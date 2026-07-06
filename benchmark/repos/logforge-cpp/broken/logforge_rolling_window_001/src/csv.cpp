#include "logforge/csv.hpp"

#include "logforge/field.hpp"

namespace logforge {

std::vector<std::string> splitRecord(const std::string& line) {
	std::vector<std::string> fields;
	std::string cur;
	bool inQuotes = false;

	for (std::size_t i = 0; i < line.size(); ++i) {
		const char c = line[i];
		if (inQuotes) {
			if (c == '"') {
				// A doubled quote stays part of the raw token; a lone quote
				// closes the quoted section.
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
			if (c == '"') {
				inQuotes = true;
				cur.push_back('"');
			} else if (c == ',') {
				fields.push_back(cur);
				cur.clear();
			} else {
				cur.push_back(c);
			}
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
