#!/bin/bash

set -e

echo "=== CLEANING ==="
rm -rf gen build doc > /dev/null

echo "=== EXPORTING ==="
mkdir -p gen/test build doc
../../scripts/export-java.py --package test --output_dir gen/test ../../testdata/Demo.bp ../../testdata/DemoDeprecated.bp

echo "=== COMPILING ==="
javac -d build ../../java/common/src/org/bluepacket/* src/test/* gen/test/*
javadoc -exclude org.bluepacket -d doc ../../java/common/src/org/bluepacket/* gen/test/*

echo "=== TESTING ==="
java -cp build test.TestBluePacket
