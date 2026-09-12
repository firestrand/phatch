# Codec and Parallel Processing

Phatch derives readable and writable image formats from the codecs registered by
the running Pillow build. `phatch --capabilities` reports each registered writer
as `image-codec-write:<extension>`. A Save output whose encoder is absent is
rejected during read-only preflight. JPEG, PNG, TIFF, GIF, and WebP are exercised
with real files. AVIF appears only when Pillow registers it. HEIF/HEIC requires
the optional `Phatch[heif]` extra; core installation does not require libheif.

`--max-workers N` accepts values from 1 through the host logical CPU count. The
default remains 1. Eligible Save jobs use the same typed engine at every worker
count: one worker executes inline, while larger counts use the spawn pool.
Eligibility requires exactly one enabled Save action, fixed numeric Resolution,
`Metadata=no`, normal overwrite behavior, and only the deterministic
`<filename>`, `<folder>`, `<subfolder>`, and `<type>` variables. JPEG target-size
constraints, nontrivial TIFF compression, `--keep`, `--resume`, `--no-save`,
repeats, dynamic resolution, and metadata preservation fall back explicitly to
the same legacy serial action/cache/context path at every worker count. They are
never silently ignored. With `--verbose`, Phatch reports the selected mode,
requested/effective count, worker PIDs, or the exact serial fallback constraint.

Workers receive a typed immutable Save specification with paths, codec options,
resolution, metadata policy, indices, dimensions, and source frame count. A
spawn initializer registers optional HEIF support before decoding. Workers
decode and encode private stage files; single-frame outputs decode only the
first source frame. The coordinator orders results, aggregates failures,
publishes transactions, advances recovery state, and removes stages. Submit and
future pool failures become per-job failures while completed work is preserved.
SIGINT cancels queued futures, terminates and boundedly joins known workers,
aborts unfinished recovery attempts, and removes stages.

A frame remains limited to 64 million pixels. Each job's memory estimate sums
the actual dimensions of every retained frame at 8 bytes per pixel plus 64 KiB
per source-frame header. Single-frame outputs account for the first decoded
frame while retaining header overhead for all source frames. Workers repeat the
dimension, per-frame pixel-limit, and memory-budget checks against the source
immediately before copying pixels. A single job above the 512 MiB budget is
rejected before decode instead of bypassing the budget at one worker. Admitted
concurrency is bounded by requested workers, job count, and the largest
frame-aware estimate. These are admission estimates, not a process RSS guarantee.

## Benchmark

Run from a synced checkout with:

```bash
uv run benchmarks/parallel.py
```

Measurements below were taken on 2026-09-10 on a 16-logical-CPU Apple Silicon
host using Pillow 11.3.0. The installed `phatch` CLI transcoded the same noise
PNG inputs to JPEG with metadata disabled and resolution fixed at 72 DPI. Three
samples of every configuration were run in deterministic randomized order using
seed 20260910. Peak memory is the sampled resident set sum of the coordinator
and all descendant workers. Requested CPU count is shown as 16; effective
workers were capped by job count to 8, 5, and 3. Times show mean and range; RSS
is the three-sample mean.

| Workload | Files | Pixels/file | Requested workers | Mean time (range), s | Mean peak RSS, MiB |
| --- | ---: | ---: | ---: | ---: | ---: |
| Small | 8 | 262,144 | 1 | 0.796 (0.784-0.803) | 158.4 |
| Small | 8 | 262,144 | 2 | 0.866 (0.864-0.868) | 158.4 |
| Small | 8 | 262,144 | 16 | 0.874 (0.855-0.885) | 322.6 |
| Medium | 5 | 2,359,296 | 1 | 0.960 (0.935-0.984) | 158.5 |
| Medium | 5 | 2,359,296 | 2 | 0.993 (0.988-0.998) | 171.3 |
| Medium | 5 | 2,359,296 | 16 | 0.935 (0.932-0.940) | 269.8 |
| Large | 3 | 9,437,184 | 1 | 1.287 (1.274-1.303) | 158.4 |
| Large | 3 | 9,437,184 | 2 | 1.259 (1.256-1.264) | 279.6 |
| Large | 3 | 9,437,184 | 16 | 1.116 (1.097-1.137) | 384.1 |

Additional spawn workers were slower for small files and at two workers for
medium files. Two workers were about 2.1% faster for large files, while the
CPU-count request was about 13.3% faster. Large-file mean RSS increased about
76.5% with two workers and 142.6% at the CPU-count request. Because gains remain
workload-dependent while memory growth is material, one inline worker remains
the conservative default. Eligible independent medium/large batches may opt
into more workers and measure on their own hardware. Higher counts are not
recommended without workload-specific memory measurements.

The RSS sampler currently requires the POSIX `ps` command, so this benchmark
harness is for local Unix-like measurements. Runtime execution itself uses the
cross-platform process-pool API and does not depend on `ps`.
