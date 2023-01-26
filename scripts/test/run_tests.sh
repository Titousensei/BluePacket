#!/bin/bash

set -e

echo "=== TESTING ==="
if (( $# == 0 ))
then
  python3 -m unittest test-libexport
else
  python3 -m unittest test-libexport.TestLibExport.$1
fi
