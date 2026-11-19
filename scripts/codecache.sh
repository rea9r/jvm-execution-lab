#!/usr/bin/env bash
# Experiment (3): code cache contents after loading 1,000 copies of Cart, calling them repeatedly, and GC
set -euo pipefail
source "$(dirname "$0")/lib.sh"

OUT=results/codecache
rm -rf "$ROOT/$OUT"
mkdir -p "$ROOT/$OUT"

in_container bash -c "
  set -e
  for i in \$(seq 1 $RUNS); do
    for n in 1000 1; do
      bash scripts/codecache-driver.sh $OUT/copies\$n-\$i $JAVA_OPTS -cp build/classes \
        -Xlog:jit+compilation=debug:file=$OUT/copies\$n-\$i/compile.log \
        Copies \$n 3000 build/copies 2> /dev/null
    done
  done
"
