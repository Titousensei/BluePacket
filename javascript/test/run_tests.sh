#!/bin/bash

set -e

echo "=== CLEANING ==="
rm -rf gen doc > /dev/null

echo "=== EXPORTING ==="
mkdir -p gen
# --runtime is resolved relative to the generated bundle (gen/gen.js)
../../scripts/export-javascript.py --output_dir gen --runtime ../../common/blue_packet.js \
    ../../testdata/Demo.bp ../../testdata/DemoDeprecated.bp ../../testdata/DemoConvert.bp ../../testdata/ListPacketTest.bp ../../testdata/RecursiveA.bp ../../testdata/RecursiveB.bp

echo "=== TESTING ==="
node TestBluePacket.js
