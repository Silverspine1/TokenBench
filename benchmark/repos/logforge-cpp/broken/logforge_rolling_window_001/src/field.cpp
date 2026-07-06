#include "logforge/field.hpp"

namespace logforge {

std::string decodeField(const std::string& raw) {
	// Only quoted tokens carry escaping. A quoted token is at least the two
	// surrounding quotes.
	if (raw.size() >= 2 && raw.front() == '"' && raw.back() == '"') {
		const std::string inner = raw.substr(1, raw.size() - 2);
		std::string out;
		out.reserve(inner.size());
		for (std::size_t i = 0; i < inner.size(); ++i) {
			// A doubled quote inside the field is a single literal quote.
			if (inner[i] == '"' && i + 1 < inner.size() && inner[i + 1] == '"') {
				out.push_back('"');
				++i;
			} else {
				out.push_back(inner[i]);
			}
		}
		return out;
	}
	return raw;
}

}  // namespace logforge
