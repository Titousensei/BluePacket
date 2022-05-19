for p in */rpc/
do
  if [ -e $p/run_tests.sh ]
  then
    echo -n $p ...
    pushd $p > /dev/null
    ./run_tests.sh > run_tests.log 2>&1
    if [ $? -eq 0 ]
    then
      echo " PASS"
    else
      echo " FAIL"
    fi
    popd > /dev/null
  fi
done
