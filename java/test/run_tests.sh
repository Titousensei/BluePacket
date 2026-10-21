#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "=== CLEANING ==="
rm -rf "$SCRIPT_DIR/gen" "$SCRIPT_DIR/build" "$SCRIPT_DIR/doc" > /dev/null

echo "=== EXPORTING ==="
mkdir -p "$SCRIPT_DIR/gen/test" "$SCRIPT_DIR/build" "$SCRIPT_DIR/doc"
python3 "$ROOT_DIR/scripts/export-java.py" --package test --output_dir "$SCRIPT_DIR/gen/test" "$ROOT_DIR/testdata/Demo.bp" "$ROOT_DIR/testdata/DemoDeprecated.bp" "$ROOT_DIR/testdata/DemoConvert.bp" "$ROOT_DIR/testdata/ListPacketTest.bp"

echo "=== COMPILING ==="
javac -Xlint:unchecked -d "$SCRIPT_DIR/build" "$ROOT_DIR/java/common/src/org/bluepacket/"*.java "$SCRIPT_DIR/src/test/"*.java "$SCRIPT_DIR/gen/test/"*.java
javadoc -exclude org.bluepacket -Xdoclint:-missing -d "$SCRIPT_DIR/doc" "$ROOT_DIR/java/common/src/org/bluepacket/"*.java "$SCRIPT_DIR/gen/test/"*.java

echo "=== TESTING ==="
java -cp "$SCRIPT_DIR/build" test.TestBluePacket
