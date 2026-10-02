#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p tests/java-classes dist
find software/desktop/src/main/java -name '*.java' > tests/java-sources.txt
javac --release 17 -encoding UTF-8 -d tests/java-classes @tests/java-sources.txt
jar --create --file dist/lezhandr-desktop-demo.jar --main-class ru.spimshaski.lezhandr.DesktopApp -C tests/java-classes .
java -jar dist/lezhandr-desktop-demo.jar --self-test > tests/results/java_tests.txt
