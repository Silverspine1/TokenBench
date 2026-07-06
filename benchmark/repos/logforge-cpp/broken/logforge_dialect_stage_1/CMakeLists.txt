cmake_minimum_required(VERSION 3.16)
project(logforge CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_library(logforge
    src/csv.cpp
    src/field.cpp
    src/parse_number.cpp
    src/stats.cpp
    src/rolling.cpp
    src/format.cpp
    src/column.cpp
    src/window.cpp
    src/render.cpp
)
target_include_directories(logforge PUBLIC include)

add_executable(logforge_cli app/main.cpp)
target_link_libraries(logforge_cli PRIVATE logforge)
