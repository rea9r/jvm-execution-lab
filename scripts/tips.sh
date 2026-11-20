#!/usr/bin/env bash
# The practical tips: startup with an AOT cache or with C1 only, and methods over the 8,000-byte limit
set -euo pipefail
source "$(dirname "$0")/lib.sh"

OUT=results/tips
rm -rf "$ROOT/$OUT"
mkdir -p "$ROOT/$OUT"
python3 "$ROOT/tools/huge_source.py" "$ROOT/build/huge"

in_container bash -c "
  set -e
  # The AOT cache cannot be made from a directory on the class path, so the classes go into a JAR as well
  jar --create --file /tmp/app.jar -C build/classes .
  java $JAVA_OPTS -XX:AOTCacheOutput=/tmp/app.aot -Xlog:aot=warning:file=$OUT/aot-create.log \
    -cp /tmp/app.jar Run split 500 10000 > /dev/null
  ls -l /tmp/app.aot | awk '{print \$5}' > $OUT/aot-size.txt
  # The same error with the class directory, kept to show what the log says
  java $JAVA_OPTS -XX:AOTCacheOutput=/tmp/dir.aot -Xlog:aot=error:file=$OUT/aot-dir-error.log \
    -cp build/classes Run split 10 10000 > /dev/null || echo exit code \$? >> $OUT/aot-dir-error.log
  ls -l /tmp/dir.aot* >> $OUT/aot-dir-error.log 2>&1 || true

  # The compilation logs go to /tmp first: writing them to the folder shared with the host can delay the JIT
  # (see the log experiment below)
  mkdir -p /tmp/logs
  for i in \$(seq 1 $RUNS); do
    java $JAVA_OPTS -cp build/classes \
      -Xlog:jit+compilation=debug:file=/tmp/logs/dir-\$i.log:timenanos Run split 500 10000 > $OUT/dir-\$i.csv 2> /dev/null
    java $JAVA_OPTS -cp /tmp/app.jar \
      -Xlog:jit+compilation=debug:file=/tmp/logs/jar-\$i.log:timenanos Run split 500 10000 > $OUT/jar-\$i.csv 2> /dev/null
    java $JAVA_OPTS -XX:AOTCache=/tmp/app.aot -cp /tmp/app.jar \
      -Xlog:jit+compilation=debug:file=/tmp/logs/aot-\$i.log:timenanos Run split 500 10000 > $OUT/aot-\$i.csv 2> /dev/null
    java $JAVA_OPTS -XX:TieredStopAtLevel=1 -cp /tmp/app.jar \
      -Xlog:jit+compilation=debug:file=/tmp/logs/c1-\$i.log:timenanos Run split 500 10000 > $OUT/c1-\$i.csv 2> /dev/null
  done

  # The log experiment: the same JAR run, writing the compilation log straight into the shared folder,
  # with the log written by the calling thread (the default) and by a separate thread (-Xlog:async)
  for i in \$(seq 1 $RUNS); do
    java $JAVA_OPTS -cp /tmp/app.jar \
      -Xlog:jit+compilation=debug:file=$OUT/logsync-\$i.log:timenanos Run split 500 10000 > $OUT/logsync-\$i.csv 2> /dev/null
    java $JAVA_OPTS -Xlog:async -cp /tmp/app.jar \
      -Xlog:jit+compilation=debug:file=$OUT/logasync-\$i.log:timenanos Run split 500 10000 > $OUT/logasync-\$i.csv 2> /dev/null
  done

  mkdir -p /tmp/huge
  javac -d /tmp/huge build/huge/*.java src-tips/HugeCall.java
  for c in Huge8000 Huge8004; do
    # The offset of the last instruction (lreturn, 1 byte), so the method is one byte longer
    echo \"\$c \$(javap -c -p -cp /tmp/huge \$c | grep lreturn | tr -d ' :' | sed 's/lreturn//')\" >> $OUT/huge-size.txt
  done
  for i in \$(seq 1 $RUNS); do
    for c in Huge8000 Huge8004; do
      java $JAVA_OPTS -cp /tmp/huge -Xlog:jit+compilation=debug:file=/tmp/logs/\$c-\$i.log \
        HugeCall \$c 5 > $OUT/\$c-\$i.csv 2> /dev/null
    done
    java $JAVA_OPTS -XX:-DontCompileHugeMethods -cp /tmp/huge -Xlog:jit+compilation=debug:file=/tmp/logs/Huge8004-forced-\$i.log \
      HugeCall Huge8004 5 > $OUT/Huge8004-forced-\$i.csv 2> /dev/null
  done
  cp /tmp/logs/*.log $OUT/
"
