#pragma once

#include <string>

namespace logforge {

// decodeFieldWith turns one raw token into its real string value under the given
// quote character. A token wrapped in that quote has the surrounding quotes
// removed and every doubled quote inside it collapsed to a single quote. A token
// with no surrounding quotes is returned unchanged.
std::string decodeFieldWith(const std::string& raw, char quote);

// decodeField is the historical entry point: it decodes using the double-quote
// character, so existing callers behave exactly as before.
std::string decodeField(const std::string& raw);

}  // namespace logforge
