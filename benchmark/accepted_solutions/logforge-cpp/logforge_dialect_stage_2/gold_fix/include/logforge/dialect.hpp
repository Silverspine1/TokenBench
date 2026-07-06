#pragma once

#include <string>

namespace logforge {

// A Dialect captures the punctuation that defines one input shape: the character
// that separates fields and the character that quotes a field so it can hold the
// separator. Different sources present their rows with different punctuation, so
// the parser is parameterised over a Dialect rather than hard-coding commas.
struct Dialect {
	char delimiter = ',';
	char quote = '"';
};

// The default dialect: comma-separated fields quoted with double quotes. The
// historical entry points use this so existing callers see no change.
inline Dialect defaultDialect() {
	return Dialect{',', '"'};
}

// Look up a named input shape. Recognised names are "csv" (comma separated) and
// "ssv" (semicolon separated); both quote with double quotes. An unrecognised
// name falls back to the default dialect.
Dialect dialectByName(const std::string& name);

}  // namespace logforge
