#include "logforge/dialect.hpp"

namespace logforge {

Dialect dialectByName(const std::string& name) {
	if (name == "ssv") {
		return Dialect{';', '"'};
	}
	if (name == "csv") {
		return Dialect{',', '"'};
	}
	return defaultDialect();
}

}  // namespace logforge
