#!/usr/bin/env bash
# Experiment (2): one method versus small methods, with and without the JIT and inlining
set -euo pipefail
source "$(dirname "$0")/lib.sh"

OUT=results/inlining
rm -rf "$ROOT/$OUT"
mkdir -p "$ROOT/$OUT"

DONTINLINE="-XX:CompileCommand=quiet -XX:CompileCommand=dontinline,Cart::subtotal -XX:CompileCommand=dontinline,Cart::withTax"
# PrintInlining is a diagnostic option. VM output goes to stderr so that it does not mix with the CSV
PRINT="-XX:+UnlockDiagnosticVMOptions -XX:+DisplayVMOutputToStderr -XX:+PrintCompilation"

in_container bash -c "
  set -e
  for i in \$(seq 1 $RUNS); do
    for v in onemethod split; do
      java $JAVA_OPTS -cp build/classes Run \$v 2000 10000 > $OUT/\$v-jit-\$i.csv 2> /dev/null
      java $JAVA_OPTS -Xint -cp build/classes Run \$v 30 10000 > $OUT/\$v-xint-\$i.csv 2> /dev/null
    done
    java $JAVA_OPTS $DONTINLINE -cp build/classes Run split 2000 10000 > $OUT/split-dontinline-\$i.csv 2> /dev/null
  done

  java $JAVA_OPTS $PRINT -XX:CompileCommand=quiet -XX:CompileCommand=PrintInlining,Cart::total \
    -cp build/classes Run split 2000 10000 > /dev/null 2> $OUT/split-inlining.log
  java $JAVA_OPTS $PRINT -XX:CompileCommand=quiet -XX:CompileCommand=PrintInlining,CartOneMethod::total \
    -cp build/classes Run onemethod 2000 10000 > /dev/null 2> $OUT/onemethod-inlining.log
  java $JAVA_OPTS $PRINT $DONTINLINE -XX:CompileCommand=PrintInlining,Cart::total \
    -cp build/classes Run split 2000 10000 > /dev/null 2> $OUT/split-dontinline-inlining.log
"
