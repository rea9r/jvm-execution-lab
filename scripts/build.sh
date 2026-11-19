#!/usr/bin/env bash
# Compile the programs with the JDK in the container
set -euo pipefail
source "$(dirname "$0")/lib.sh"

in_container bash -c '
  set -e
  rm -rf build
  javac -d build/classes src/*.java
  # Cart again, outside the class path, for the class loader copies in the code cache experiment
  javac -d build/copies src/Cart.java src-copies/CartWorkload.java
  java -version 2>&1 | head -1
'
