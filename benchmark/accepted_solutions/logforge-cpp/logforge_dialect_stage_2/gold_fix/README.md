# logforge

A small C++17 command-line tool for parsing CSV/log data and reporting
statistics. It is a single library plus a thin CLI, with no external
dependencies, so it builds with any C++17 compiler.

## Layout

```
include/logforge   public headers
src                library sources: csv, field, parse_number, stats, rolling, format
app/main.cpp       CLI: summarize a numeric column of a CSV file
fixtures           sample input data
docs               behaviour notes
tests_visible      smoke tests (python tests_visible/run_visible.py)
CMakeLists.txt     CMake build
```

## Building

With CMake:

```
cmake -S . -B build && cmake --build build
```

Or directly:

```
g++ -std=c++17 -I include src/*.cpp app/main.cpp -o logforge_cli
```

## Tests

```
python tests_visible/run_visible.py
```
