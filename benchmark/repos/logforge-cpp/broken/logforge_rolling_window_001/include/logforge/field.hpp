#pragma once

#include <string>

namespace logforge {

// decodeField turns one raw CSV token into its real string value. A token
// wrapped in double quotes has the surrounding quotes removed and every doubled
// quote ("") inside it collapsed to a single quote. A token with no surrounding
// quotes is returned unchanged.
std::string decodeField(const std::string& raw);

}  // namespace logforge
