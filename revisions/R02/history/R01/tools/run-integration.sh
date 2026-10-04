#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
cmake -S firmware -B tests/build >/dev/null
cmake --build tests/build -j2 >/dev/null
bash tools/build-desktop.sh
tests/build/controller_sim 18765 >tests/results/integration-simulator.log 2>&1 &
PID=$!; trap 'kill "$PID" 2>/dev/null || true' EXIT
sleep 0.3
java -cp dist/lezhandr-desktop-demo.jar ru.spimshaski.lezhandr.IntegrationTest 18765 | tee tests/results/java_native_integration.txt
