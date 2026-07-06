#include "logforge/field.hpp"

namespace logforge {

std::string decodeFieldWith(const std::string& raw, char quote) {
	// A quoted token is one that begins with the dialect's quote character. A
	// quote that appears anywhere other than the first character carries no
	// special meaning, so a token that does not begin with a quote is returned
	// exactly as-is.
	if (raw.empty() || raw.front() != quote) {
		return raw;
	}

	std::string out;
	out.reserve(raw.size());
	std::size_t i = 1;  // skip the opening quote
	bool closed = false;
	for (; i < raw.size(); ++i) {
		if (raw[i] == quote) {
			// A doubled quote inside the quoted section is one literal quote.
			if (i + 1 < raw.size() && raw[i + 1] == quote) {
				out.push_back(quote);
				++i;
			} else {
				// A lone quote closes the quoted section; whatever follows it on
				// the same field is appended literally.
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

std::string decodeField(const std::string& raw) {
	return decodeFieldWith(raw, '"');
}

}  // namespace logforge
