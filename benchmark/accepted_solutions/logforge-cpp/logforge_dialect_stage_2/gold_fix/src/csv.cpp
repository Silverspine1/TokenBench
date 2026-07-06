#include "logforge/csv.hpp"

#include "logforge/field.hpp"

namespace logforge {

std::vector<std::string> splitRecordWith(const std::string& line, const Dialect& dialect) {
	std::vector<std::string> fields;
	std::string cur;
	bool inQuotes = false;
	// The quote character only opens a quoted section when it is the very first
	// character of a field. Anywhere else it is an ordinary character.
	bool atFieldStart = true;

	for (std::size_t i = 0; i < line.size(); ++i) {
		const char c = line[i];
		if (inQuotes) {
			if (c == dialect.quote) {
				// A doubled quote stays part of the raw token; a lone quote closes
				// the quoted section.
				if (i + 1 < line.size() && line[i + 1] == dialect.quote) {
					cur.push_back(dialect.quote);
					cur.push_back(dialect.quote);
					++i;
				} else {
					inQuotes = false;
					cur.push_back(dialect.quote);
				}
			} else {
				cur.push_back(c);
			}
		} else {
			if (c == dialect.delimiter) {
				fields.push_back(cur);
				cur.clear();
				atFieldStart = true;
			} else if (c == dialect.quote && atFieldStart) {
				inQuotes = true;
				cur.push_back(dialect.quote);
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

Record parseLineWith(const std::string& line, const Dialect& dialect) {
	Record record;
	for (const std::string& raw : splitRecordWith(line, dialect)) {
		record.push_back(decodeFieldWith(raw, dialect.quote));
	}
	return record;
}

std::vector<std::string> splitRecord(const std::string& line) {
	return splitRecordWith(line, defaultDialect());
}

Record parseLine(const std::string& line) {
	return parseLineWith(line, defaultDialect());
}

}  // namespace logforge
