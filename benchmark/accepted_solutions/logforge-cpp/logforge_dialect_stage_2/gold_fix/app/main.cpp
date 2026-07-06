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
#include "logforge/stream.hpp"

int main(int argc, char** argv) {
	if (argc < 3) {
		std::cerr << "usage: logforge <file.csv> <column-index> [input-shape] [--stream]\n";
		return 2;
	}
	const std::string path = argv[1];
	const int col = std::atoi(argv[2]);
	// An optional third argument selects the input shape by name (e.g. "csv" or
	// "ssv"); when omitted the default comma-separated shape is used.
	std::string shape;
	bool stream = false;
	for (int i = 3; i < argc; ++i) {
		const std::string arg = argv[i];
		if (arg == "--stream") {
			stream = true;
		} else {
			shape = arg;
		}
	}
	const logforge::Dialect dialect =
	    shape.empty() ? logforge::defaultDialect() : logforge::dialectByName(shape);

	if (col < 0) {
		std::cerr << "column index must be non-negative\n";
		return 2;
	}

	std::ifstream in(path);
	if (!in) {
		std::cerr << "cannot open " << path << "\n";
		return 1;
	}

	logforge::Summary s;
	if (stream) {
		// Streaming mode: fold the file in line by line without materialising all
		// records, reusing the same input-shape behaviour.
		s = logforge::streamSummary(in, static_cast<std::size_t>(col), dialect,
		                            /*skipHeader=*/true);
	} else {
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
		const std::vector<double> values =
		    logforge::numericColumn(records, static_cast<std::size_t>(col));
		s = logforge::summarize(values);
	}
	std::cout << logforge::formatColumns(logforge::renderSummary(s));
	return 0;
}
