# Bounded batch workers and performance

The engine defaults to sequential processing. Independent process workers are opt-in for workflows whose outputs can be resolved before execution.

```python
import multiprocessing
from phatch.core.batch import run_batch

if __name__ == '__main__':
    result = run_batch(
        actions,
        inputs,
        {'workers': 2, 'memory_budget_mb': 2048},
        mp_context=multiprocessing.get_context('spawn'),
    )
```

```bash
phatch --console --workers 2 --memory-budget-mb 2048 recipe.phatch photos/
```

Python scripts using workers need an import-safe main entry point. The library accepts a caller-supplied multiprocessing context and otherwise uses spawn. The console launcher is guarded against child-process reentry.

## Ownership and deterministic output

Workers reconstruct independent action instances from serialized fields. Image state and action caches belong to each input; native encoder thread limits remain separate controls and default to one AVIF encoder thread.

The parent plans all outputs before dispatch. Each worker commits to its reserved paths, preserving global input/repeat/folder indices and input ordering in results. Planned rename destinations use a no-overwrite commit: a racing external writer causes a visible failure rather than redirecting a worker into another reservation.

The parent also owns progress callbacks, error decisions and resume journals. Callbacks run on the thread that called `run_batch`. Progress acknowledgments allow callback-triggered cancellation before the corresponding action starts. Skip/ignore error decisions retain their normal continuation behavior. Worker count is bounded from 1 to 64, and submitted unfinished jobs never exceed effective workers.

Each job has its own duplex event/decision pipe. A startup handshake lets the parent close its duplicate child endpoint, so an interrupted message produces EOF. Cancellation uses a separate parent-written notification pipe; workers poll it without consuming the notification or acquiring a shared lock. The parent writes once and closes its endpoints after pool shutdown. This avoids the shared queue-feeder and Event locks that crash stress testing showed could be stranded by worker termination. The [Python multiprocessing reference](https://docs.python.org/3.12/library/multiprocessing.html#pipes-and-queues) describes termination and shared-lock/queue hazards.

[Crash stress evidence](../benchmarks/results/worker-transport-stress.json) retains the failing configurations and 40 final repetitions of eight crash cases on each of Python 3.12.14, 3.13.15 and 3.14.8: 960 checks pass without timeout. Regression cases include a partially written pipe message after commit and termination during cancellation checking. These supplement normal callback/cancellation, failure-isolation and owned-output tests.

Supported built-in pipelines use the audited image transforms, Save and Variants, including supported sequence policies. Side-effecting plugins, source-overwriting operations and unresolved output paths are rejected. Importable custom plugins can declare `parallel_safe = True`; their module must expose the standard Action class and serializable fields. This declaration accepts responsibility for independent processing, rather than providing a security sandbox. Workers copy parent file/font dictionaries to preserve alias resolution; [plugin contracts](PLUGIN_CONTRACTS.md) describes external dependencies and the other execution declarations.

## Memory and failure limits

The default total worker address-space budget is 2,048 MiB. Admission estimates decoded pixels and multiple native working/export copies, plus interpreter state. Effective concurrency is reduced when necessary; an input whose reservation exceeds the entire budget fails setup.

Each child receives an operating-system `RLIMIT_AS` cap, whose configured limits sum to at most the worker budget. The budget excludes the parent and multiprocessing helper processes. Address space differs from resident memory; native codecs, mapped libraries and allocator behavior affect both. Worker mode requires an operating system exposing this resource limit and fails clearly when it is unavailable. Sequential mode remains available.

Allocation failure becomes an input failure; tests verify that other jobs continue and produce valid outputs. An abrupt process exit stops the broken pool and reports affected jobs, leaving undispatched work unstarted. Before encoding an atomic output, the child waits for the parent to register the temporary file and reserved target. The parent holds a descriptor to that inode until the transaction finishes, preventing inode reuse. After pool shutdown, it removes only registered temporaries whose inode still matches, and recovers committed images and JSON artifacts even when a child died before returning a result. Replacement files at temporary paths are retained. Failed jobs remain incomplete in the journal and are replayed on resume. Normal encoder failure and cooperative cancellation use the same atomic transactions.

This recovery covers registered transactions while the parent survives. A child killed between creating its temporary and completing the registration can leave an unregistered empty file; recovery deliberately avoids filename-pattern deletion because another writer may own a matching file. Parent termination and power-loss durability are separate boundaries.

Cancellation stops new submissions and signals running jobs at existing processing boundaries. A native encoder already running returns before cancellation can take effect. Previously committed outputs remain reported. When stop-on-error is enabled, already-running independent jobs finish; at most effective-workers jobs are in flight.

Reports include execution diagnostics: backend, requested/effective worker counts, maximum in-flight jobs, worker budget and per-worker address-space limit.

## Measured local results

Measurements were collected on an aarch64 Linux system reporting Cortex-X925 CPUs, 20 logical CPUs and approximately 122 GiB of RAM, using Python 3.14.8 and Pillow 12.3.0. They use generated gradient JPEGs and synthetic metadata, rather than production photos. Three fresh-process measurements per configuration after event/cancellation transport isolation supply the medians below. Two-worker runs use the default 2,048 MiB budget.

| Workload | Inputs | Sequential seconds | Two-worker seconds | Speed ratio | Peak aggregate RSS, sequential / workers |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Resize/export | 8 × 2400 × 1600 | 0.449 | 0.478 | 0.94× | 72.3 / 217.0 MiB |
| Watermark/export | 8 × 2400 × 1600 | 1.211 | 0.871 | 1.39× | 116.1 / 296.8 MiB |
| Metadata/color/export | 8 × 2400 × 1600 | 1.176 | 0.810 | 1.45× | 111.4 / 278.7 MiB |
| Large-image resize/export | 4 × 6000 × 4000 | 1.243 | 0.850 | 1.46× | 236.3 / 472.4 MiB |

[Current raw measurements](../benchmarks/results/r11-isolated-transport.json) retain all 24 repetitions. The small resize workload is faster sequentially in this run; workers remain opt-in. [Preceding recovery measurements](../benchmarks/results/r11-crash-recovery.json) and [original baseline and worker measurements](../benchmarks/results/r11-local.json) remain available. Every measured configuration produced the same ordered output-pixel SHA-256 for its workload, including the original measurements. Differences between separate measurement sessions do not isolate the transport change's cost from ordinary runtime variation. Metadata/color inputs contain two synthetic EXIF fields and an sRGB profile; the pipeline applies sharing metadata and sRGB conversion. This is a focused metadata/color case, not a measurement of every metadata backend or very large metadata payloads.

Additional measurements on the same environment cover larger metadata, pages and resource-dependent journaled processing. Each configuration has three fresh-process repetitions; [all 18 measurements](../benchmarks/results/r11-expanded-workloads.json) retain input bytes, metadata payload sizes, frame counts, output hashes and resume timings.

| Workload | Inputs | Sequential seconds | Two-worker seconds | Speed ratio | Peak aggregate RSS, sequential / workers |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Native metadata preservation | 8 × 2400 × 1600 JPEG | 0.543 | 0.488 | 1.11× | 116.2 / 276.7 MiB |
| Multipage TIFF preservation | 4 × 8 pages, 1200 × 800 | 1.011 | 0.721 | 1.40× | 167.6 / 400.6 MiB |
| Watermark with resource journal | 8 × 2400 × 1600 JPEG | 1.335 | 0.939 | 1.42× | 115.4 / 293.9 MiB |

The metadata fixture contains 29,912 bytes of EXIF and 30,955 bytes of XMP per input, plus an sRGB profile. Reopened exports retain the expected comment, date, GPS, XMP and ICC. TIFF inputs total approximately 87.9 MiB; all eight output pages retain their source pixels, descriptions, LZW compression and profiles. Every workload verifies deterministic source-based names and matching ordered pixel hashes across worker settings. Journaled watermarking fingerprints its resource and verifies all eight outputs on resume; median resume times are 11.1 ms sequentially and 11.7 ms with two workers.

[Adjacent watermark controls](../benchmarks/results/r11-journal-controls.json) retain another 12 measurements: three pairs of plain and journaled runs per worker setting. Plain/journaled medians are 1.130/1.392 seconds sequentially and 0.842/0.900 seconds with two workers. Median paired increases are 0.260 and 0.061 seconds respectively. These increases include hashing, output verification and atomic journal writes; they do not isolate individual costs. Resume verification takes a median 11.2/11.8 ms. All control pixel hashes match. Three samples provide local evidence, without establishing statistical significance or coverage of every metadata backend and platform.

[Resource-overlap planning controls](../benchmarks/results/r11-resource-guard.json) retain twelve later fresh-process runs after protecting read-resource destinations. Plain/journaled watermark medians are 1.142/1.371 seconds sequentially and 0.879/0.932 seconds with two workers, with aggregate RSS medians of 116.3/115.2 MiB and 300.7/293.7 MiB respectively. The preceding plain/journaled controls were 1.130/1.392 and 0.842/0.900 seconds. Pixel hashes match across both sessions and resume verification passes. These small differences include runtime variation and do not isolate the planning change's cost; workers remain opt-in.

Elapsed time covers batch execution, including pool startup and initial journal work when enabled. Resume timing is recorded separately. Fixture generation and reopened-output checks are outside batch elapsed time, while RSS is sampled across the complete benchmark process and its descendants every 10 ms, including fixture generation and output verification. Sampling can miss short peaks. These measurements show a local throughput/memory tradeoff and do not establish universal speedups, scaling efficiency or a hard aggregate RSS limit.

The initial sequential baseline and all repeated measurements are retained in [r11-local.json](../benchmarks/results/r11-local.json). An initial resize profile recorded about 0.502 seconds in batch execution, with Scale and Save totaling about 0.404 seconds. Native resizing and export were the main processing costs, supporting independent process jobs while isolating mutable plugin modules.

## Reproduce measurements

```bash
uv run --locked python benchmarks/batch_workloads.py --workload resize --workers 1
uv run --locked python benchmarks/batch_workloads.py --workload resize --workers 2
uv run --locked python benchmarks/batch_workloads.py --workload watermark --workers 2
uv run --locked python benchmarks/batch_workloads.py --workload metadata --workers 2
uv run --locked python benchmarks/batch_workloads.py --workload large --workers 2 --count 4
uv run --locked python benchmarks/batch_workloads.py --workload metadata_payload --workers 2
uv run --locked python benchmarks/batch_workloads.py --workload pages --workers 2 --count 4
uv run --locked python benchmarks/batch_workloads.py --workload journal_watermark --workers 2
```

Fresh-process benchmarking exposed removed Pillow resampling names in automatic Scale/Fit and a directory-creation race. Both were corrected before accepting worker results. Native metadata also remains usable when an importable pyexiv2 namespace lacks the legacy adapter API.

Resource and process behavior follow Python's [process executor documentation](https://docs.python.org/3.12/library/concurrent.futures.html#concurrent.futures.ProcessPoolExecutor) and [resource-limit documentation](https://docs.python.org/3.12/library/resource.html#resource.RLIMIT_AS).
