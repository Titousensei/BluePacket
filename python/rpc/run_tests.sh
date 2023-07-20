#!/bin/bash

set -e

echo "=== CLEANING ==="
rm -f *_tests.log > /dev/null

echo "=== COMPILING ==="
pushd ../../java/rpc/
./build.sh
popd

./build.sh > run_tests.log 2>&1

echo "=== SERVER ==="

trap 'kill $(jobs -pr)' EXIT
java -cp ../../java/rpc/build example.rpc.ExampleServer >> run_tests.log 2>&1 &
sleep 1

echo "=== TESTING ==="

echo "Clients testing" >> run_tests.log
./run_client.sh Add 1 2 3 4 >> result_tests.log 2>> run_tests.log
./run_client.sh Mean Arithmetic 4 36 45 50 75 >> result_tests.log 2>> run_tests.log
./run_client.sh Mean Geometric 4 36 45 50 75 >> result_tests.log 2>> run_tests.log
./run_client.sh Mean Harmonic 4 36 45 50 75 >> result_tests.log 2>> run_tests.log

echo "=== NEGATIVE TESTING ==="

./run_client.sh Fake 1 2 3 4 2>&1 | grep "^Exception" >> result_tests.log 2>> run_tests.log
./run_client.sh Mean Quantic 1 2 3 4 2>&1 | grep "^Exception" >> result_tests.log 2>> run_tests.log
./run_client.sh Mean Harmonic 2>&1 | grep "^Exception" >> result_tests.log 2>> run_tests.log

echo "=== RESULTS ==="

diff -uBbw result_tests.expected result_tests.log
