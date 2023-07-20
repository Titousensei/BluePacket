#!/bin/bash

set -e

echo "=== CLEANING ==="
rm -rf gen build > /dev/null

echo "=== EXPORTING ==="
mkdir -p gen/example/packet build
../../scripts/export-java.py --package example.packet --output_dir gen/example/packet ../../testdata/example_rpc.bp

echo "=== COMPILING ==="
javac -d build ../../java/common/src/org/bluepacket/* src/org/bluepacket/network/* src/example/rpc/* gen/example/packet/*
