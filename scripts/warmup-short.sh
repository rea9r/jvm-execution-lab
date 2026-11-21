#!/usr/bin/env bash
# Repeated calls with a short loop: Cart.total over 10 items, 200,000 times. Each call is a few tens of nanoseconds,
# close to the resolution of System.nanoTime, so what to read is the round in which each compilation started. The
# per-call CSV (200,000 rows per run) stays in build/; results/ keeps the compilation logs and the timelines.
set -euo pipefail
source "$(dirname "$0")/lib.sh"

OUT=results/warmup-short
CSV=build/warmup-short
rm -rf "$ROOT/$OUT" "$ROOT/$CSV"
mkdir -p "$ROOT/$OUT" "$ROOT/$CSV"

in_container bash -c "
  set -e
  mkdir -p /tmp/logs
  for i in \$(seq 1 $RUNS); do
    java $JAVA_OPTS -cp build/classes \
      -Xlog:jit+compilation=debug:file=/tmp/logs/short-\$i.log:timenanos \
      Run split 200000 10 > $CSV/short-\$i.csv 2> /dev/null
  done
  cp /tmp/logs/*.log $OUT/
"
for i in $(seq 1 "$RUNS"); do
  python3 "$ROOT/tools/timeline.py" "$ROOT/$CSV/short-$i.csv" "$ROOT/$OUT/short-$i.log" Cart > "$ROOT/$OUT/timeline-$i.txt"
done
