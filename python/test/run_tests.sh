#!/bin/bash

echo "=== CLEANING ==="
rm -rf gen doc > /dev/null

echo "=== EXPORTING ==="
mkdir -p gen/test
../../scripts/export-python.py --output_dir gen/test ../../testdata/Demo.bp ../../testdata/DemoDeprecated.bp ../../testdata/DemoConvert.bp

echo "=== DOCUMENTATION ==="
if [[ $(type -P doxygen) ]]
then
  doxygen Doxyfile
else
  echo skipping: doxygen not found
fi

echo "=== TESTING ==="
python3 TestBluePacket.py
