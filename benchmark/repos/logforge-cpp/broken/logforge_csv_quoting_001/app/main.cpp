// logforge CLI: read a CSV file, treat one column as numbers, and print a
// statistics summary. This is a thin, runnable entry point over the library.
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include "logforge/csv.hpp"
#include "logforge/format.hpp"
#include "logforge/parse_number.hpp"
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

	std::vector<double> values;
	std::string line;
	bool header = true;
	while (std::getline(in, line)) {
		if (header) {
			header = false;
			continue;
		}
		const logforge::Record rec = logforge::parseLine(line);
		if (col < 0 || static_cast<std::size_t>(col) >= rec.size()) {
			continue;
		}
		if (auto v = logforge::parseDouble(rec[col])) {
			values.push_back(*v);
		}
	}

	const logforge::Summary s = logforge::summarize(values);
	std::vector<std::vector<std::string>> rows = {
		{"count", logforge::formatFixed(static_cast<double>(s.count), 0)},
		{"sum", logforge::formatFixed(s.sum, 2)},
		{"mean", logforge::formatFixed(s.mean, 2)},
		{"min", logforge::formatFixed(s.min, 2)},
		{"max", logforge::formatFixed(s.max, 2)},
	};
	std::cout << logforge::formatColumns(rows);
	return 0;
}
