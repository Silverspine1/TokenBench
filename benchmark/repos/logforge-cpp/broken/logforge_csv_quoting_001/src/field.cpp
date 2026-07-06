#include "logforge/field.hpp"

namespace logforge {

std::string decodeField(const std::string& raw) {
	if (raw.size() >= 2 && raw.front() == '"' && raw.back() == '"') {
		return raw.substr(1, raw.size() - 2);
	}
	return raw;
}

}  // namespace logforge
