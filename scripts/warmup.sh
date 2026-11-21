#!/usr/bin/env bash
# Experiment (1): call Cart.total repeatedly, with and without the JIT
set -euo pipefail
source "$(dirname "$0")/lib.sh"

OUT=results/warmup
rm -rf "$ROOT/$OUT"
mkdir -p "$ROOT/$OUT"

# The logs go to /tmp inside the container and are copied afterwards: writing them to the folder shared with the
# host delays the compiler threads and slows the first calls
in_container bash -c "
  set -e
  mkdir -p /tmp/logs
  for i in \$(seq 1 $RUNS); do
    java $JAVA_OPTS -cp build/classes \
      -Xlog:jit+compilation=debug:file=/tmp/logs/jit-\$i.log:timenanos \
      Run split 500 10000 > $OUT/jit-\$i.csv 2> /dev/null
    java $JAVA_OPTS -Xint -cp build/classes \
      -Xlog:jit+compilation=debug:file=/tmp/logs/xint-\$i.log:timenanos \
      Run split 50 10000 > $OUT/xint-\$i.csv 2> /dev/null
  done
  cp /tmp/logs/*.log $OUT/
"
