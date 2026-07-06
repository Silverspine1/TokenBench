#pragma once

#include <string>
#include <vector>

namespace logforge {

// A Record is the decoded list of fields parsed from one input line.
using Record = std::vector<std::string>;

}  // namespace logforge
