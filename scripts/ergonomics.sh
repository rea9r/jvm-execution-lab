#!/usr/bin/env bash
# The GC, the number of JIT threads and the maximum heap that the JVM picks from the CPU limit and the memory of the
# container, read from -XX:+PrintFlagsFinal
set -euo pipefail
source "$(dirname "$0")/lib.sh"

OUT=results/ergonomics
mkdir -p "$ROOT/$OUT"

flags() {
  # $1: docker options (split on spaces on purpose), $2: extra JVM options
  # shellcheck disable=SC2086
  docker run --rm $1 "$IMAGE" java $2 -XX:+PrintFlagsFinal -version < /dev/null 2> /dev/null |
    awk '$2 == "UseSerialGC" || $2 == "UseG1GC" || $2 == "CICompilerCount" || $2 == "MaxHeapSize" { v[$2] = $4 }
         END {
           gc = v["UseG1GC"] == "true" ? "G1" : (v["UseSerialGC"] == "true" ? "Serial" : "other")
           printf "%s\t%s\t%d MB\n", gc, v["CICompilerCount"], v["MaxHeapSize"] / 1048576
         }'
}

{
  printf "docker options\tJVM options\tGC\tJIT threads\tmax heap\n"
  while IFS='|' read -r docker jvm; do
    printf "%s\t%s\t%s\n" "$docker" "${jvm:--}" "$(flags "$docker" "$jvm")"
  done <<'EOF'
--cpus=4 --memory=2g|
--cpus=2 --memory=2g|
--cpus=1.5 --memory=2g|
--cpus=1 --memory=2g|
--cpus=0.5 --memory=2g|
--cpus=4 --memory=1792m|
--cpus=4 --memory=1791m|
--cpus=4 --memory=1g|
--cpus=1 --memory=2g|-XX:ActiveProcessorCount=4
EOF
} > "$ROOT/$OUT/ergonomics.tsv"
cat "$ROOT/$OUT/ergonomics.tsv"
