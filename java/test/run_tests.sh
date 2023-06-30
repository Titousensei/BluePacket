#!/bin/bash

set -e

echo "=== CLEANING ==="
rm -rf gen build doc > /dev/null

echo "=== EXPORTING ==="
mkdir -p gen/test build doc
../../scripts/export-java.py --package test --output_dir gen/test ../../testdata/Demo.bp

echo "=== COMPILING ==="
javac -d build ../../java/common/src/org/bluepacket/network/* src/test/* gen/test/*
javadoc -exclude org.bluepacket.network -d doc ../../java/common/src/org/bluepacket/network/* gen/test/*

echo "=== TESTING ==="
java -cp build test.TestBluePacket
