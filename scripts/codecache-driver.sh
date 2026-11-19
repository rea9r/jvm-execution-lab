#!/usr/bin/env bash
# Runs inside the container: start Copies, and record jcmd output each time it prints "PHASE <name> <pid>"
# usage: codecache-driver.sh <out-dir> <java args ...>
set -euo pipefail

out=$1
shift
mkdir -p "$out"

coproc JAVA { exec java "$@"; }
java_pid=$JAVA_PID

while IFS= read -r line <&"${JAVA[0]}"; do
  case "$line" in
    PHASE*)
      read -r _ name pid <<< "$line"
      jcmd "$pid" Compiler.codecache > "$out/$name.codecache.txt"
      jcmd "$pid" Compiler.codelist > "$out/$name.codelist.txt"
      jcmd "$pid" VM.metaspace > "$out/$name.metaspace.txt"
      echo >&"${JAVA[1]}"
      ;;
    *)
      echo "$line"
      ;;
  esac
done
wait "$java_pid"
