#pragma once

// Legacy compatibility surface produced by an upstream code import. Everything
// the parser, statistics and formatting paths need was folded into a single
// catch-all translation unit (src/core.cpp) and re-declared here under the short
// internal names the import generated. Call sites were rewired to include this
// single header instead of the per-concern public headers.
#include <cstddef>
#include <optional>
#include <string>
#include <vector>

namespace lf {

// One decoded input line: the list of field values.
using Rec = std::vector<std::string>;

// Descriptive statistics of a column of numbers.
struct Sm {
	std::size_t count = 0;
	double sum = 0.0;
	double mean = 0.0;
	double min = 0.0;
	double max = 0.0;
};

// --- parser surface ------------------------------------------------------
Rec pl(const std::string& line);                    // split + decode into a record
std::optional<double> pd(const std::string& text);  // parse a numeric field

// --- statistics surface --------------------------------------------------
Sm sm(const std::vector<double>& values);
std::vector<double> nc(const std::vector<Rec>& records, std::size_t index);
std::vector<double> rm(const std::vector<double>& values, std::size_t window);

// --- formatting surface --------------------------------------------------
std::string ff(double value, int precision);
std::string fc(const std::vector<std::vector<std::string>>& rows);
std::vector<std::vector<std::string>> rs(const Sm& summary);

}  // namespace lf
