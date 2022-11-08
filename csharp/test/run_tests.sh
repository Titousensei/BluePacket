#!/bin/bash

set -e

echo "=== CLEANING ==="
rm -rf gen build doc > /dev/null

echo "=== EXPORTING ==="
mkdir -p gen/test build
../../scripts/export-csharp.py --namespace Test --output_dir gen/test ../../testdata/Demo.bp ../../testdata/DemoDeprecated.bp

echo "=== COMPILING ==="
if [[ $(type -P mono-csc) ]]
then
  mono-csc -out:build/Test ../../csharp/common/src/* src/* gen/test/*
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
