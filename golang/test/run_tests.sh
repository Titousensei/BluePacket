#!/bin/bash

go_package=gen
go_import=github.com/bluepacketdemo

echo "=== CLEANING ==="
rm -rf $go_package > /dev/null

echo "=== EXPORTING ==="
mkdir -p $go_package
../../scripts/export-golang.py --package $go_package --output_dir $go_package ../../testdata/Demo.bp ../../testdata/DemoDeprecated.bp

pushd $go_package
go mod init $go_import
popd

echo "=== DOCUMENTATION ==="
go doc

echo "=== TESTING ==="
go test
