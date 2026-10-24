#!/bin/bash

set -e

echo "=== CLEANING ==="
rm -rf gen build doc > /dev/null

echo "=== EXPORTING ==="
mkdir -p gen/test build
../../scripts/export-csharp.py --namespace Test --output_dir gen/test ../../testdata/Demo.bp ../../testdata/DemoDeprecated.bp ../../testdata/DemoConvert.bp ../../testdata/RecursiveA.bp ../../testdata/RecursiveB.bp

echo "=== COMPILING ==="
if [[ $(type -P mono-csc) ]]
then
  mono-csc -out:build/Test ../../csharp/common/src/*.cs src/*.cs gen/test/*.cs
else
  echo skipping: mono-csc not found
fi

echo "=== DOCUMENTATION ==="
if [[ $(type -P doxygen) ]]
then
  doxygen Doxyfile
else
  echo skipping: doxygen not found
fi

echo "=== TESTING ==="
if [[ $(type -P mono-csc) ]]
then
  mono build/Test Test.TestBluePacket
else
  echo skipping: mono not found
fi
