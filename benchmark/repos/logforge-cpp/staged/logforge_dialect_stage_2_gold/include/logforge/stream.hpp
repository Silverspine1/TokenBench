#pragma once

#include <cstddef>
#include <istream>

#include "logforge/dialect.hpp"
#include "logforge/stats.hpp"

namespace logforge {

// streamSummary reads an input stream one line at a time and accumulates the
// summary statistics of a single numeric column, under the given input shape,
// without ever holding the whole input in memory. It parses each line with the
// supplied dialect, reads the requested column, and folds finite numeric values
// into a running summary. When skipHeader is true the first line is treated as a
// header and ignored. The returned Summary matches what summarize() would give
// for the same column read in full.
Summary streamSummary(std::istream& in, std::size_t column, const Dialect& dialect,
                      bool skipHeader);

}  // namespace logforge
