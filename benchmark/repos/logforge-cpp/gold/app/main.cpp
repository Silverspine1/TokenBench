// logforge CLI: read a CSV file, treat one column as numbers, and print a
// statistics summary. This is a thin, runnable entry point over the library.
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include "logforge/column.hpp"
#include "logforge/csv.hpp"
#include "logforge/format.hpp"
#include "logforge/record.hpp"
#include "logforge/render.hpp"
#include "logforge/stats.hpp"

int main(int argc, char** argv) {
	if (argc < 3) {
		std::cerr << "usage: logforge <file.csv> <column-index>\n";
		return 2;
	}
	const std::string path = argv[1];
	const int col = std::atoi(argv[2]);

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
		records.push_back(logforge::parseLine(line));
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
