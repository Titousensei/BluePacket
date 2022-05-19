#!/bin/bash

set -e

echo "=== CLEANING ==="
rm -f *_tests.log > /dev/null

echo "=== COMPILING ==="
./build.sh > run_tests.log 2>&1

echo "=== TESTING ==="

echo "Starting Server"  >> run_tests.log
./run_server.sh >> run_tests.log 2>&1 &
sleep 1

echo "Clients testing"  >> run_tests.log
./run_client.sh Add 1 2 3 4 >> result_tests.log 2>> run_tests.log
./run_client.sh Mean Arithmetic 4 36 45 50 75 >> result_tests.log 2>> run_tests.log
./run_client.sh Mean Geometric 4 36 45 50 75 >> result_tests.log 2>> run_tests.log
./run_client.sh Mean Harmonic 4 36 45 50 75 >> result_tests.log 2>> run_tests.log

echo "=== NEGATIVE TESTING ==="
./run_client.sh Fake 1 2 3 4  2>&1 | grep "^Exception" >> result_tests.log
./run_client.sh Mean Quantic 1 2 3 4 2>&1 | grep "^Exception" >> result_tests.log
./run_client.sh Mean Harmonic 2>&1 | grep "^Exception" >> result_tests.log

echo "Starting 2nd Server on same port" >> run_tests.log
./run_server.sh 2>&1 | grep "\[RpcServer\] exiting" >> result_tests.log &
sleep 1

echo "=== CLEANING UP ==="

pkill -f example.rpc.ExampleServer
diff -uBbw result_tests.expected result_tests.log
