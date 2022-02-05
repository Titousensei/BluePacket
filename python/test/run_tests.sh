#!/bin/bash

echo "=== CLEANING ==="
rm -rf gen build > /dev/null

echo "=== EXPORTING ==="
mkdir -p gen/test build
../../scripts/export-python.py --output_dir gen/test ../../testdata/Demo.bp

echo "=== TESTING ==="
python3 TestBluePacket.py