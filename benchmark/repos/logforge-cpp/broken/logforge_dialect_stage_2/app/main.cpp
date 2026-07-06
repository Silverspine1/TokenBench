// logforge CLI: read a CSV file, treat one column as numbers, and print a
// statistics summary. This is a thin, runnable entry point over the library.
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include "logforge/column.hpp"
#include "logforge/csv.hpp"
#include "logforge/dialect.hpp"
#include "logforge/format.hpp"
#include "logforge/record.hpp"
#include "logforge/render.hpp"
#include "logforge/stats.hpp"

int main(int argc, char** argv) {
	if (argc < 3) {
		std::cerr << "usage: logforge <file.csv> <column-index> [input-shape]\n";
		return 2;
	}
	const std::string path = argv[1];
	const int col = std::atoi(argv[2]);
	// An optional third argument selects the input shape by name (e.g. "csv" or
	// "ssv"); when omitted the default comma-separated shape is used.
	const logforge::Dialect dialect =
	    (argc >= 4) ? logforge::dialectByName(argv[3]) : logforge::defaultDialect();

	std::ifstream in(path);
	if (!in) {
		std::cerr << "cannot open " << path << "\n";
		return 1;
	}

	std::vector<logforge::Record> records;
	std::string line;
	bool header = true;
	while (std::getline(in, line)) {
		if (header) {
			header = false;
			continue;
		}
		records.push_back(logforge::parseLineWith(line, dialect));
	}
	if (col < 0) {
		std::cerr << "column index must be non-negative\n";
		return 2;
	}

	const std::vector<double> values =
	    logforge::numericColumn(records, static_cast<std::size_t>(col));
	const logforge::Summary s = logforge::summarize(values);
	std::cout << logforge::formatColumns(logforge::renderSummary(s));
	return 0;
}
