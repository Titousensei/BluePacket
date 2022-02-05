#!/bin/bash

echo "=== CLEANING ==="
rm -rf gen build > /dev/null

echo "=== EXPORTING ==="
mkdir -p gen/test build
../../scripts/export-java.py --package test --output_dir gen/test ../../testdata/Demo.bp

echo "=== COMPILING ==="
javac -d build ../../java/common/src/org/bluesaga/network/* src/test/* gen/test/*

echo "=== TESTING ==="
java -cp build test.TestBluePacket
