#!/usr/bin/env bash
# Experiment (1): call Cart.total repeatedly, with and without the JIT
set -euo pipefail
source "$(dirname "$0")/lib.sh"

OUT=results/warmup
rm -rf "$ROOT/$OUT"
mkdir -p "$ROOT/$OUT"

in_container bash -c "
  set -e
  for i in \$(seq 1 $RUNS); do
    java $JAVA_OPTS -cp build/classes \
      -Xlog:jit+compilation=debug:file=$OUT/jit-\$i.log:timenanos \
      Run split 500 10000 > $OUT/jit-\$i.csv 2> /dev/null
    java $JAVA_OPTS -Xint -cp build/classes \
      -Xlog:jit+compilation=debug:file=$OUT/xint-\$i.log:timenanos \
      Run split 50 10000 > $OUT/xint-\$i.csv 2> /dev/null
  done
"
