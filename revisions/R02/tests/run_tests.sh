#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p tests/results tests/build tests/java_classes
cmake -S firmware -B tests/build > tests/results/cmake_R02.log
cmake --build tests/build -j2 >> tests/results/cmake_R02.log
ctest --test-dir tests/build --output-on-failure | tee tests/results/ctest_R02.log
tests/build/core_tests | tee tests/results/core_R02.log
javac --release 17 -d tests/java_classes software/desktop/src/main/java/ru/spimshaski/lezhandr/*.java
java -cp tests/java_classes ru.spimshaski.lezhandr.DesktopApp --self-test | tee tests/results/java_R02.log
tests/build/controller_sim 18765 > tests/results/simulator_R02.log 2>&1 &
SIM_PID=$!
trap 'kill "$SIM_PID" 2>/dev/null || true' EXIT
sleep 0.5
java -cp tests/java_classes ru.spimshaski.lezhandr.IntegrationTest 18765 | tee tests/results/integration_R02.log
