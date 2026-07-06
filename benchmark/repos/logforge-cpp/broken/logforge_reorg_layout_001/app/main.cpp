// logforge CLI: read a CSV file, treat one column as numbers, and print a
// statistics summary. This is a thin, runnable entry point over the library.
// After the legacy import the entry point talks to the consolidated surface in
// blob.hpp rather than per-concern public headers.
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include "blob.hpp"

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

	std::vector<lf::Rec> records;
	std::string line;
	bool header = true;
	while (std::getline(in, line)) {
		if (header) {
			header = false;
			continue;
		}
		records.push_back(lf::pl(line));
	}
	if (col < 0) {
		std::cerr << "column index must be non-negative\n";
		return 2;
	}

	const std::vector<double> values = lf::nc(records, static_cast<std::size_t>(col));
	const lf::Sm s = lf::sm(values);
	std::cout << lf::fc(lf::rs(s));
	return 0;
}
