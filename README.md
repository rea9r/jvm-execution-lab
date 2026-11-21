# jvm-execution-lab

Experiments that follow one short Java class from its bytecode to the native code the JIT compiler produces, and to the code cache that keeps that code. Each experiment starts from a prediction and checks it against three records of the same run: the time of every call, the JIT compilation log, and `jcmd` output.

All measurements run in the `eclipse-temurin:25.0.5_8-jdk` image (HotSpot, JDK 25.0.5) with 4 CPUs (`--cpuset-cpus=0-3`), 2 GB of memory and a fixed 512 MB heap. With these settings the JVM uses 3 JIT compiler threads, G1, and a 240 MB code cache split into three code heaps. The compilation behaviour shown here is HotSpot's; other JDK versions, CPU counts and runs compile at different moments.

## The code

Every experiment runs this class (`src/Cart.java`):

```java
public class Cart {
    public record Item(int price, int quantity) {}

    static long subtotal(Item item) {
        return (long) item.price() * item.quantity();
    }

    static long withTax(long amount) {
        return amount * 110 / 100;
    }

    public static long total(Item[] items) {
        long sum = 0;
        for (Item item : items) {
            sum += withTax(subtotal(item));
        }
        return sum;
    }
}
```

`total` calls `subtotal` and `withTax` at bytecode offsets 27 and 30 (`javap -c -p Cart`). Its loop starts at offset 11, which is where on-stack replacement (OSR) enters compiled code in the middle of a call.

## Requirements

- Docker, with at least 4 CPUs and 2 GB of memory available to containers
- Python 3 (standard library only) for the reports in `tools/`

## Usage

```bash
scripts/build.sh
```

Compiles the programs inside the container.

```bash
scripts/warmup.sh
scripts/warmup-short.sh
scripts/inlining.sh
scripts/codecache.sh
scripts/taxed.sh
scripts/tips.sh
```

Each script runs one experiment inside the container and replaces `results/<experiment>/`. Experiments run 5 times by default; set `RUNS` to change it (`RUNS=3 scripts/codecache.sh`).

## What the logs show

| Record | How it is taken | How to read it |
| --- | --- | --- |
| Time of each call | `src/Run.java` stores `System.nanoTime()` before and after each call and prints a CSV after the last one | Nothing is printed while measuring |
| JIT compilations | `-Xlog:jit+compilation=debug:file=...:timenanos` | Same format as `-XX:+PrintCompilation`. A line is printed when a compilation **starts**. Calls switch to the new code when it is installed, which shows up as the `made not entrant` line of the version it replaces. The `timenanos` decoration is the `System.nanoTime()` clock, so the log lines up with the CSV (`tools/timeline.py`) |
| Inlining decisions | `-XX:+UnlockDiagnosticVMOptions -XX:CompileCommand=PrintInlining,Cart::total -XX:+PrintCompilation` | C2 prints its decisions when the compilation finishes, so the tree belongs to the compilation printed just before it |
| Code cache usage | `jcmd <pid> Compiler.codecache` | `used` of each code heap and the number of nmethods |
| Code cache contents | `jcmd <pid> Compiler.codelist` | One line per compiled method: compile ID, tier, state (in JDK 25, 0 is in use and 1 is not entrant), method and address range. OSR versions are not marked; look up the compile ID in the compilation log |

The compile ID is the same in all three logs, which is how a line in the code cache list is traced back to the compilation that produced it.

## Experiments

### Warmup: does a method get faster when it is called again and again?

`scripts/warmup.sh` calls `Cart.total` on 10,000 items 500 times, and 50 times with `-Xint` (interpreter only).

```bash
python3 tools/timeline.py results/warmup/jit-1.csv results/warmup/jit-1.log Cart
python3 tools/warmup_report.py results/warmup
```

The first prints, for each compilation of `Cart` and `Cart$Item`, the call during which it started or was replaced. The second splits each run at the points where `Cart.total` switched to new code and prints the median time per stage.

| Calls | Time per call (median of 5 runs) | What runs `Cart.total` |
| --- | ---: | --- |
| 1st | 780 µs | The interpreter. `subtotal` and `withTax` reach tier 3, and `price()` and `quantity()` reach tier 1, during this call |
| 2nd to 6th | 217 µs | Still the interpreter, calling compiled `subtotal` and `withTax` |
| C1 (from the 7th, until about the 56th) | 31 µs | C1 code with full profiling (tier 3), first entered through OSR in the 7th call |
| C2 OSR version ready (about the 57th to the 81st) | 48 µs | Each call starts in the tier 3 code and leaves it for the C2 OSR version |
| C2 (from about the 82nd) | 5.9 µs | C2 code (tier 4) |
| `-Xint`, 1st | 756 µs | |
| `-Xint`, 2nd onwards | 562 µs | |

In all 5 runs, the C1 OSR version started in the 7th call, the C2 OSR version was installed in the 57th to 63rd, and the normal C2 version in the 81st to 88th. With `-Xint`, the log has two lines, both native method entries (`Continuation::enterSpecial` and `doYield`); no Java method is compiled.

The slower stage between the two C2 versions comes from OSR. Once a C2 OSR version exists, the tier 3 code deoptimizes its own frame when its loop counter overflows (`Runtime1::counter_overflow` in `c1_Runtime1.cpp`), so that the interpreter can enter the OSR version. To stop this from happening on every call, the compilation policy also compiles the normal entry with C2 (`CompilationPolicy::call_event` in `compilationPolicy.cpp`: "avoid OSRs during each invocation of the method"). In the log, the C2 compilation of the normal entry starts within two calls after the tier 3 OSR version is made not entrant with the reason `OSR invalidation of lower level`.

### Warmup with a short loop

`scripts/warmup-short.sh` calls `Cart.total` over 10 items, 200,000 times. A call takes a few tens of nanoseconds, close to the resolution of `System.nanoTime()`, so the timelines in `results/warmup-short/timeline-*.txt` are what to read (the per-call CSV stays in `build/`).

In all 5 runs, no OSR version of `total` was compiled. Its normal code was compiled at tier 3 in the 214th to 217th call and at tier 4 from the 1,906th to 1,953rd call in 4 runs (616th and 2,430th in the other). With 10 iterations per call, the backedge count would reach the OSR threshold of 60,000 only after 6,000 calls; the invocation and combined thresholds are reached first.

### Inlining: does splitting code into small methods cost a call each time?

`scripts/inlining.sh` compares `Cart.total` with `CartOneMethod.total`, which does the same work in one method. It runs each with the JIT (2,000 calls, median of the last 1,000) and with `-Xint` (30 calls, median of the last 20). It also runs `Cart` with `-XX:CompileCommand=dontinline` for `subtotal` and `withTax`.

```bash
python3 tools/steady.py 1001 2000 results/inlining/split-jit-*.csv
```

| | `-Xint` | JIT | JIT, `subtotal` and `withTax` not inlined |
| --- | ---: | ---: | ---: |
| One method (`CartOneMethod`) | 339.9 µs | 6.0 µs | |
| Small methods (`Cart`) | 552.7 µs | 6.2 µs | 18.7 µs |

Medians of 5 runs. The inlining logs (`results/inlining/*-inlining.log`) show why the two versions run at the same speed with the JIT. C1 (tier 3) already inlines `subtotal`, `withTax`, `price()` and `quantity()`; C2 reports `subtotal` and `withTax` as `inline (hot)` and the record accessors as `accessor`. With `dontinline`, both compilers report `failed to inline: disallowed by CompileCommand`, and the call costs come back.

### Code cache: what is kept, and what makes it grow?

`scripts/codecache.sh` loads `Cart` 1,000 times through separate class loaders, so the same class file becomes 1,000 separate classes. A single JVM goes through these phases, and `scripts/codecache-driver.sh` records `jcmd` output at each one:

1. right after start
2. after loading every copy and calling it once with 10 items, which is too few calls for anything in `Cart` to be compiled
3. after calling every copy 3,000 times with 1,000 items
4. after each of three `System.gc()` calls

```bash
python3 tools/codecache_report.py results/codecache/copies1000-1
```

| Phase | non-nmethods | profiled | non-profiled | nmethods | `Cart` entries | Metaspace |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Started | 1,218 KB | 44 KB | 20 KB | 83 | 0 | 0.39 MB |
| Loaded, called once | 1,224 KB | 891 KB | 151 KB | 601 | 0 | 7.82 MB |
| Called 3,000 times | 1,224 KB | 5,518 KB | 3,776 KB | 11,607 | 11,000 | 9.07 MB |
| After the 1st GC | 1,224 KB | 5,531 KB | 3,780 KB | 11,622 | 11,000 | 9.08 MB |
| After the 2nd GC | 1,224 KB | 1,568 KB | 3,775 KB | 7,563 | 7,000 | 9.08 MB |

All three runs gave nearly the same numbers.

- Before any of our code runs, the code cache already holds about 1.2 MB in non-nmethods (the interpreter and other code the JVM generates for itself) and about 80 nmethods.
- Loading the 1,000 classes adds 7.4 MB of Metaspace but no `Cart` entries. The code cache grows by about 1 MB anyway, because the JDK code that loads classes gets compiled.
- After the hot phase, each copy has 11 entries: `price()` and `quantity()` at tier 1, the `Item` constructor at tier 3, and `subtotal`, `withTax`, `total` and the OSR version of `total` twice each, as not-entrant C1 code and as tier 4 code in use. About 1% of the not-entrant ones were compiled at tier 2 instead of tier 3, the tier C1 uses while the C2 queue is long.
- From the loaded phase to the hot phase, profiled and non-profiled grow by 8,252 KB. The `Cart` entries add up to 8,246 KB when each one is measured from its start to the start of the next entry. The range that `Compiler.codelist` prints ends where the code (instructions and stubs) ends, so it leaves out the data that each nmethod keeps after its code.
- The not-entrant C1 versions are still there after the first GC and gone after the second.

`results/codecache/copies1-*` holds the same phases with a single copy, small enough to read line by line. In `copies1-1`, the 11 entries have compile IDs 90 to 100, the same IDs as in the compilation log in that directory.

### Tax rules behind an interface

`scripts/taxed.sh` uses `TaxedCart`, which applies a tax rule through an interface with three implementations. `taxed1` to `taxed3` use one to three of them from the start; `shift` uses only one for the first 1,000 calls and all three afterwards.

| Implementations seen at the call site | Time per call (median of 5 runs) | C2 inlining decision for `TaxRule::apply` |
| --- | ---: | --- |
| 1 | 7.4 µs | `inline (hot)` |
| 2 | 9.4 µs | `inline (hot)` for both implementations |
| 3 | 93 µs | `failed to inline: virtual call` |

In `shift`, both C2 versions of `total` are made not entrant with the reason `uncommon trap` in the 1,001st and 1,002nd calls, and `total` is compiled again at tier 3 and tier 4. The order of these events was the same in all 5 runs, but the time per call afterwards was not: about 93 µs in 4 runs and about 49 µs in 1. This is not explained yet.

### Startup, the 8,000-byte limit and logging

`scripts/tips.sh` backs the practical tips at the end of the article. It runs `Run split 500 10000` five times each with the class directory, with a JAR, with a JAR and an AOT cache (`-XX:AOTCacheOutput` / `-XX:AOTCache`, JDK 25), and with a JAR and C1 only (`-XX:TieredStopAtLevel=1`), interleaved. `python3 tools/tips_report.py results/tips` prints the table (median of 5 runs, µs).

| Run | 1st call | 2nd-6th | 101st-500th | Sum of 1st-100th |
| --- | ---: | ---: | ---: | ---: |
| Class directory | 537.0 | 213.8 | 5.9 | 4.56 ms |
| JAR | 445.3 | 221.5 | 6.2 | 4.62 ms |
| JAR + AOT cache | 207.8 | 10.6 | 6.1 | 1.19 ms |
| JAR + C1 only | 358.8 | 206.6 | 7.2 | 2.27 ms |
| JAR, log written to the shared folder | 1003.8 | 645.6 | 6.0 | 7.63 ms |
| The same with `-Xlog:async` | 452.5 | 201.5 | 6.0 | 4.52 ms |

- The AOT cache cannot be made with a non-empty directory on the class path: the run ends with exit code 1 and no cache, and the reason shows only with `-Xlog:aot` (`results/tips/aot-dir-error.log`). This is why the other runs use a JAR.
- Writing the compilation log into the folder shared with the host (`-v`) delayed the first compilations of `subtotal` and `withTax` in 4 of 5 JAR runs, and they were compiled at tier 2 instead of tier 3. `-Xlog:async` removes the delay. Runs from the class directory were not affected; why is not known. The script therefore writes the logs for measurement to `/tmp` and copies them afterwards.
- `tools/huge_source.py` writes methods of exactly 8,000 and 8,004 bytes of bytecode. Called 20,000 times, the 8,000-byte one is compiled at tier 3 and 4 (8.0 ms); the 8,004-byte one is never compiled (66.1 ms) unless `-XX:-DontCompileHugeMethods` is given (8.0 ms).

## Layout

| Path | Contents |
| --- | --- |
| `src/` | `Cart`, the variants, `Run` (calls `total` and records each call) and `Copies` (code cache phases) |
| `src-copies/` | `CartWorkload`, compiled into `build/copies/` with `Cart`, outside the class path, for the class loader copies |
| `src-tips/` | `HugeCall`, which calls the methods written by `tools/huge_source.py` |
| `scripts/` | Build and experiment scripts. `lib.sh` holds the image, container and heap settings |
| `tools/` | Reports on the results |
| `tools/figures/` | Scripts that draw the figures and charts, and turn the Archify diagrams into static SVGs for the article |
| `figures/` | The figures embedded in the article. `figures/archify/` holds the sources of the Archify diagrams |
| `results/` | The recorded results that the numbers above come from |

## License

MIT
