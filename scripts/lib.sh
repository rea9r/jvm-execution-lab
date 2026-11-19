# Settings shared by the experiment scripts. Source this file; do not run it.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="eclipse-temurin:25.0.5_8-jdk"

# 4 CPUs without a CPU quota, so that the JVM sees 4 processors and is not throttled
DOCKER_OPTS=(--rm -i --cpuset-cpus=0-3 --memory=2g -v "$ROOT:/lab" -w /lab)

# Fixed heap so that every run has the same GC setup
JAVA_OPTS="-Xms512m -Xmx512m"

RUNS="${RUNS:-5}"

in_container() {
  docker run "${DOCKER_OPTS[@]}" "$IMAGE" "$@"
}
