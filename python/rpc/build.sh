#!/bin/bash

set -e

echo "=== CLEANING ==="
rm -rf gen build > /dev/null

echo "=== EXPORTING ==="
mkdir -p gen/example/packet build
../../scripts/export-python.py --output_dir gen/example/packet ../../testdata/example_rpc.bp
