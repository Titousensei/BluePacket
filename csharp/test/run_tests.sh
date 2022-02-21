#!/bin/bash

set -e

echo "=== CLEANING ==="
rm -rf gen build > /dev/null

echo "=== EXPORTING ==="
mkdir -p gen/test build
../../scripts/export-csharp.py --namespace Test --output_dir gen/test ../../testdata/Demo.bp

echo "=== COMPILING ==="
mono-csc -out:build/Test ../../csharp/common/src/* src/* gen/test/*

echo "=== TESTING ==="
mono build/Test Test.TestBluePacket
