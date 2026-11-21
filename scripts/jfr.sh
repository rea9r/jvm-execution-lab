#!/usr/bin/env bash
# How many JIT events JFR records for the warmup run (Run split 500 10000 from a JAR): with the default settings, and
# with the compilation threshold at 0 ms and the inlining events turned on
set -euo pipefail
source "$(dirname "$0")/lib.sh"

OUT=results/jfr
rm -rf "$ROOT/$OUT"
mkdir -p "$ROOT/$OUT"

in_container bash -s -- "$JAVA_OPTS" "$RUNS" <<'EOF' > "$ROOT/$OUT/counts.tsv"
set -e
JAVA_OPTS=$1
RUNS=$2
jar --create --file /tmp/app.jar -C build/classes .
# The number of events of a type in a recording; a type with no events is not listed by jfr summary
count() { jfr summary "$1" | awk -v e="$2" '$1 == e { c = $2 } END { print c + 0 }'; }
printf 'settings\trun\tjdk.Compilation\tjdk.CompilerInlining\tjdk.Deoptimization\n'
for i in $(seq 1 "$RUNS"); do
  java $JAVA_OPTS -XX:StartFlightRecording:filename=/tmp/default-$i.jfr \
    -cp /tmp/app.jar Run split 500 10000 > /dev/null 2>&1
  java $JAVA_OPTS "-XX:StartFlightRecording:filename=/tmp/lowered-$i.jfr,jdk.Compilation#threshold=0ms,jdk.CompilerInlining#enabled=true" \
    -cp /tmp/app.jar Run split 500 10000 > /dev/null 2>&1
  for s in default lowered; do
    f=/tmp/$s-$i.jfr
    printf '%s\t%s\t%s\t%s\t%s\n' "$s" "$i" "$(count $f jdk.Compilation)" "$(count $f jdk.CompilerInlining)" "$(count $f jdk.Deoptimization)"
  done
done
EOF
cat "$ROOT/$OUT/counts.tsv"
