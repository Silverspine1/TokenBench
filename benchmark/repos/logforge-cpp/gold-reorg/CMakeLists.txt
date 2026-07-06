cmake_minimum_required(VERSION 3.16)
project(logforge CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

file(GLOB_RECURSE LOGFORGE_SOURCES CONFIGURE_DEPENDS src/*.cpp)

add_library(logforge ${LOGFORGE_SOURCES})
target_include_directories(logforge PUBLIC include)

add_executable(logforge_cli app/main.cpp)
target_link_libraries(logforge_cli PRIVATE logforge)
