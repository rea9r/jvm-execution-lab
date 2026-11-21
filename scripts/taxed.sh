#!/usr/bin/env bash
# Candidate for chapter 5: tax rules behind an interface, with 1 to 3 implementations, and a change after warming up
set -euo pipefail
source "$(dirname "$0")/lib.sh"

OUT=results/taxed
rm -rf "$ROOT/$OUT"
mkdir -p "$ROOT/$OUT"

PRINT="-XX:+UnlockDiagnosticVMOptions -XX:+DisplayVMOutputToStderr -XX:+PrintCompilation"

in_container bash -c "
  set -e
  mkdir -p /tmp/logs
  for i in \$(seq 1 $RUNS); do
    for v in taxed1 taxed2 taxed3 shift; do
      java $JAVA_OPTS -cp build/classes \
        -Xlog:jit+compilation=debug:file=/tmp/logs/\$v-\$i.log:timenanos \
        Run \$v 2000 10000 > $OUT/\$v-\$i.csv 2> /dev/null
    done
  done
  cp /tmp/logs/*.log $OUT/
  for v in taxed1 taxed2 taxed3 shift; do
    java $JAVA_OPTS $PRINT -XX:CompileCommand=quiet -XX:CompileCommand=PrintInlining,TaxedCart::total \
      -cp build/classes Run \$v 2000 10000 > /dev/null 2> $OUT/\$v-inlining.log
  done
"
