cmake_minimum_required(VERSION 3.10)
project(BMS_Diagnostic_ECU CXX)

set(CMAKE_CXX_STANDARD 17)

# Inclusions des headers (Eigen cloné localement)
include_directories(${CMAKE_SOURCE_DIR}/include)

# Exécutable du calculateur C++
add_executable(ecu_diag src/main.cpp)
