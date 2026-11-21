#!/usr/bin/env bash
# The warmup run from the class directory, with the compilation log written to /tmp in the container or straight into
# the folder shared with the host, interleaved. The JAR runs of the same comparison are in scripts/tips.sh.
set -euo pipefail
source "$(dirname "$0")/lib.sh"

OUT=results/logdest-dir
rm -rf "$ROOT/$OUT"
mkdir -p "$ROOT/$OUT"

in_container bash -s -- "$JAVA_OPTS" "$RUNS" "$OUT" <<'EOF'
set -e
JAVA_OPTS=$1
RUNS=$2
OUT=$3
mkdir -p /tmp/logs
for i in $(seq 1 "$RUNS"); do
  java $JAVA_OPTS -cp build/classes \
    -Xlog:jit+compilation=debug:file=/tmp/logs/inside-$i.log:timenanos Run split 500 10000 > "$OUT/inside-$i.csv" 2> /dev/null
  java $JAVA_OPTS -cp build/classes \
    -Xlog:jit+compilation=debug:file=$OUT/shared-$i.log:timenanos Run split 500 10000 > "$OUT/shared-$i.csv" 2> /dev/null
done
cp /tmp/logs/*.log "$OUT/"
EOF
