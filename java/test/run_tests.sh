#!/bin/bash

set -e

echo "=== CLEANING ==="
rm -rf gen build doc > /dev/null

echo "=== EXPORTING ==="
mkdir -p gen/test build doc
../../scripts/export-java.py --package test --output_dir gen/test ../../testdata/Demo.bp

echo "=== COMPILING ==="
javac -d build ../../java/common/src/org/bluesaga/network/* src/test/* gen/test/*
javadoc -exclude org.bluesaga.network -d doc ../../java/common/src/org/bluesaga/network/* gen/test/*

echo "=== TESTING ==="
java -cp build test.TestBluePacket
